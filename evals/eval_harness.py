#!/usr/bin/env python3
"""Simple multi-skill eval harness for EOL Daily Coach skill prompts."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "skills" / "registry.json"
SCENARIOS_PATH = ROOT / "evals" / "scenarios.json"
CONFIG_PATH = ROOT / "evals" / "eval_config.json"
RUBRIC_PATH = ROOT / "evals" / "judge_rubric.md"

SQS_WEIGHTS = {
    "activation_fit": 0.20,
    "conversation_control": 0.20,
    "tiny_next_action": 0.20,
    "tone": 0.15,
    "handoff_behavior": 0.15,
    "state_update_contract": 0.10,
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_skill_registry(root: Path = ROOT) -> list[dict[str, Any]]:
    data = load_json(root / "skills" / "registry.json")
    skills = data.get("skills")
    if not isinstance(skills, list) or not skills:
        raise ValueError("skills/registry.json must contain a non-empty skills array")

    seen: set[str] = set()
    for skill in skills:
        skill_id = skill.get("id")
        prompt_path = skill.get("prompt_path")
        if not skill_id or not isinstance(skill_id, str):
            raise ValueError("Every skill needs a string id")
        if skill_id in seen:
            raise ValueError(f"Duplicate skill id: {skill_id}")
        seen.add(skill_id)
        if not prompt_path or not isinstance(prompt_path, str):
            raise ValueError(f"{skill_id} needs prompt_path")
        if not (root / prompt_path).exists():
            raise ValueError(f"{skill_id} prompt_path does not exist: {prompt_path}")
    return skills


def format_active_skill_context(skill_id: str, session: dict[str, Any]) -> str:
    return "\n".join(
        [
            "[ACTIVE DAILY SKILL]",
            f"skillId: {skill_id}",
            f"status: {session.get('status', 'active')}",
            f"phase: {session.get('phase', 'start')}",
            f"stateJson: {json.dumps(session.get('state', {}), ensure_ascii=False)}",
            "",
            "This skill owns the conversation until it calls skill_update with status completed, handoff, or cancelled.",
        ]
    )


def _format_history(history: list[dict[str, str]]) -> str:
    if not history:
        return "(none)"
    lines = []
    for turn in history:
        role = str(turn.get("role", "user")).strip().lower()
        label = "Assistant" if role == "assistant" else "User"
        lines.append(f"{label}: {turn.get('content', '')}")
    return "\n".join(lines)


def build_skill_input(scenario: dict[str, Any], skill_prompt: str) -> str:
    session = scenario.get("active_session") or {"status": "active", "phase": "start", "state": {}}
    return "\n\n".join(
        [
            "You are evaluating an Experiment of Life Daily Coach skill turn.",
            format_active_skill_context(str(scenario["skill_id"]), session),
            "[SKILL PROMPT]",
            skill_prompt.strip(),
            "[CONVERSATION HISTORY]",
            _format_history(scenario.get("history") or []),
            "[USER MESSAGE]",
            f"User: {scenario.get('message', '')}",
        ]
    )


def recompute_sqs(judge: dict[str, Any]) -> float:
    return round(sum(float(judge.get(key, 0)) * weight for key, weight in SQS_WEIGHTS.items()), 2)


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _make_client():
    from openai import OpenAI

    base_url = os.environ.get("OPENAI_BASE_URL") or None
    kwargs: dict[str, Any] = {"api_key": os.environ["OPENAI_API_KEY"]}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def _chat_text(client: Any, *, model: str, system: str, user: str) -> tuple[str, float]:
    started = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return response.choices[0].message.content or "", elapsed_ms


def select_scenarios(
    scenarios: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    skill_id: str | None = None,
    scenario_id: str | None = None,
    max_count: int | None = None,
) -> list[dict[str, Any]]:
    allowed = set(config.get("scenario_ids") or [])
    selected = [scenario for scenario in scenarios if scenario["id"] in allowed]
    if skill_id:
        selected = [scenario for scenario in selected if scenario["skill_id"] == skill_id]
    if scenario_id:
        selected = [scenario for scenario in selected if scenario["id"] == scenario_id]
    if max_count is not None:
        selected = selected[: max(1, max_count)]
    return selected


def run_eval(
    *,
    prompt_file: Path | None = None,
    skill_id: str | None = None,
    scenario_id: str | None = None,
    max_count: int | None = None,
    output_json: Path | None = None,
) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for model-backed evals")

    registry = {skill["id"]: skill for skill in load_skill_registry(ROOT)}
    scenarios = select_scenarios(
        load_json(SCENARIOS_PATH)["scenarios"],
        load_json(CONFIG_PATH),
        skill_id=skill_id,
        scenario_id=scenario_id,
        max_count=max_count,
    )
    rubric = RUBRIC_PATH.read_text(encoding="utf-8")
    client = _make_client()
    coach_model = os.environ.get("EVAL_COACH_MODEL", "gpt-4.1-mini")
    judge_model = os.environ.get("EVAL_JUDGE_MODEL", "gpt-4.1-mini")

    rows = []
    for scenario in scenarios:
        skill = registry[scenario["skill_id"]]
        skill_prompt_path = prompt_file or (ROOT / skill["prompt_path"])
        skill_prompt = skill_prompt_path.read_text(encoding="utf-8")
        assembled = build_skill_input(scenario, skill_prompt)
        coach_response, latency_ms = _chat_text(
            client,
            model=coach_model,
            system="You are the EOL Daily Coach. Follow the active skill prompt and tool contract.",
            user=assembled,
        )
        judge_prompt = "\n\n".join(
            [
                rubric,
                f"Scenario expected behavior: {scenario.get('expected_behavior', '')}",
                "Scenario anti-patterns: " + json.dumps(scenario.get("anti_patterns") or []),
                "Coach response:",
                coach_response,
            ]
        )
        judge_text, _judge_latency_ms = _chat_text(
            client,
            model=judge_model,
            system="You are a strict JSON-only evaluator.",
            user=judge_prompt,
        )
        judge = _extract_json_object(judge_text)
        judge["sqs"] = recompute_sqs(judge)
        rows.append(
            {
                "scenario_id": scenario["id"],
                "skill_id": scenario["skill_id"],
                "sqs": judge["sqs"],
                "latency_ms": round(latency_ms, 1),
                "coach_response": coach_response,
                "judge": judge,
            }
        )

    result = {
        "mean_sqs": round(sum(row["sqs"] for row in rows) / len(rows), 2) if rows else 0.0,
        "per_scenario": rows,
    }
    if output_json:
        write_json(output_json, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--skill-id")
    parser.add_argument("--scenario-id")
    parser.add_argument("--max", type=int, dest="max_count")
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--print-assembled-input", action="store_true")
    args = parser.parse_args()

    if args.print_assembled_input:
        registry = {skill["id"]: skill for skill in load_skill_registry(ROOT)}
        scenarios = select_scenarios(
            load_json(SCENARIOS_PATH)["scenarios"],
            load_json(CONFIG_PATH),
            skill_id=args.skill_id,
            scenario_id=args.scenario_id,
            max_count=1,
        )
        if not scenarios:
            raise SystemExit("No scenario matched")
        scenario = scenarios[0]
        prompt_path = args.prompt_file or (ROOT / registry[scenario["skill_id"]]["prompt_path"])
        print(build_skill_input(scenario, prompt_path.read_text(encoding="utf-8")))
        return 0

    result = run_eval(
        prompt_file=args.prompt_file,
        skill_id=args.skill_id,
        scenario_id=args.scenario_id,
        max_count=args.max_count,
        output_json=args.output_json,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
