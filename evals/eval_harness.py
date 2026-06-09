#!/usr/bin/env python3
"""Pack-based eval harness for EOL Daily Coach skill prompts."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
PACKS_DIR = ROOT / "packs"
DEFAULT_PACK_SLUG = "task_initiation"

REQUIRED_PACK_FIELDS = (
    "id",
    "slug",
    "title",
    "skill_prompt",
    "scenarios",
    "judge_rubric",
    "mutation_notes",
    "mutation_enabled",
    "implemented",
    "score_weights",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def pack_path(pack: dict[str, Any], key: str) -> Path:
    return Path(str(pack["_pack_dir"])) / str(pack[key])


def _load_pack_file(pack_json_path: Path) -> dict[str, Any]:
    pack = load_json(pack_json_path)
    missing = [field for field in REQUIRED_PACK_FIELDS if field not in pack]
    if missing:
        raise ValueError(f"{pack_json_path} missing required fields: {', '.join(missing)}")
    pack["_pack_dir"] = str(pack_json_path.parent)

    for file_key in ("skill_prompt", "scenarios", "judge_rubric", "mutation_notes"):
        if not pack_path(pack, file_key).exists():
            raise ValueError(f"{pack['slug']} {file_key} file does not exist: {pack[file_key]}")

    weights = pack.get("score_weights")
    if not isinstance(weights, dict) or not weights:
        raise ValueError(f"{pack['slug']} score_weights must be a non-empty object")
    return pack


def discover_packs(root: Path = ROOT) -> list[dict[str, Any]]:
    pack_paths = sorted((root / "packs").glob("*/pack.json"))
    packs = [_load_pack_file(path) for path in pack_paths]
    seen_slugs: set[str] = set()
    seen_ids: set[str] = set()
    for pack in packs:
        slug = str(pack["slug"])
        pack_id = str(pack["id"])
        if slug in seen_slugs:
            raise ValueError(f"Duplicate pack slug: {slug}")
        if pack_id in seen_ids:
            raise ValueError(f"Duplicate pack id: {pack_id}")
        seen_slugs.add(slug)
        seen_ids.add(pack_id)
    return packs


def load_pack(root: Path = ROOT, slug: str = DEFAULT_PACK_SLUG) -> dict[str, Any]:
    for pack in discover_packs(root):
        if pack["slug"] == slug:
            return pack
    raise ValueError(f"Unknown pack: {slug}")


def load_pack_scenarios(pack: dict[str, Any]) -> list[dict[str, Any]]:
    data = load_json(pack_path(pack, "scenarios"))
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError(f"{pack['slug']} scenarios must contain a non-empty scenarios array")
    seen: set[str] = set()
    for scenario in scenarios:
        scenario_id = scenario.get("id")
        if not scenario_id:
            raise ValueError(f"{pack['slug']} scenario missing id")
        if scenario_id in seen:
            raise ValueError(f"{pack['slug']} duplicate scenario id: {scenario_id}")
        seen.add(str(scenario_id))
        if scenario.get("skill_id") != pack["id"]:
            raise ValueError(f"{pack['slug']} scenario {scenario_id} must use skill_id {pack['id']}")
    return scenarios


def select_scenarios(
    scenarios: list[dict[str, Any]],
    *,
    scenario_id: str | None = None,
    max_count: int | None = None,
) -> list[dict[str, Any]]:
    selected = list(scenarios)
    if scenario_id:
        selected = [scenario for scenario in selected if scenario["id"] == scenario_id]
    if max_count is not None:
        selected = selected[: max(1, max_count)]
    return selected


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


def build_skill_input(pack: dict[str, Any], scenario: dict[str, Any], skill_prompt: str) -> str:
    session = scenario.get("active_session") or {"status": "active", "phase": "start", "state": {}}
    return "\n\n".join(
        [
            "You are evaluating an Experiment of Life Daily Coach skill turn.",
            format_active_skill_context(str(pack["id"]), session),
            "[SKILL PROMPT]",
            skill_prompt.strip(),
            "[CONVERSATION HISTORY]",
            _format_history(scenario.get("history") or []),
            "[USER MESSAGE]",
            f"User: {scenario.get('message', '')}",
        ]
    )


def build_judge_prompt(pack: dict[str, Any], scenario: dict[str, Any], rubric: str, coach_response: str) -> str:
    scenario_context = {
        "scenario_id": scenario.get("id"),
        "skill_id": pack.get("id"),
        "active_session": scenario.get("active_session") or {},
        "history": scenario.get("history") or [],
        "message": scenario.get("message", ""),
    }
    return "\n\n".join(
        [
            rubric,
            f"Pack: {pack['title']} ({pack['id']})",
            "Scenario context:",
            json.dumps(scenario_context, indent=2, ensure_ascii=False),
            f"Scenario expected behavior: {scenario.get('expected_behavior', '')}",
            "Scenario anti-patterns: " + json.dumps(scenario.get("anti_patterns") or []),
            "Coach response:",
            coach_response,
        ]
    )


def recompute_sqs(judge: dict[str, Any], pack: dict[str, Any]) -> float:
    weights = pack["score_weights"]
    return round(sum(float(judge.get(key, 0)) * float(weight) for key, weight in weights.items()), 2)


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

    base_url = normalized_openai_base_url()
    kwargs: dict[str, Any] = {"api_key": os.environ["OPENAI_API_KEY"]}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def normalized_openai_base_url() -> str | None:
    raw_base_url = os.environ.get("OPENAI_BASE_URL")
    base_url = raw_base_url.strip() if raw_base_url and raw_base_url.strip() else None
    if raw_base_url is not None and base_url is None:
        os.environ.pop("OPENAI_BASE_URL", None)
    return base_url


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


def run_eval(
    *,
    pack_slug: str = DEFAULT_PACK_SLUG,
    prompt_file: Path | None = None,
    scenario_id: str | None = None,
    max_count: int | None = None,
    output_json: Path | None = None,
) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for model-backed evals")

    pack = load_pack(ROOT, pack_slug)
    scenarios = select_scenarios(load_pack_scenarios(pack), scenario_id=scenario_id, max_count=max_count)
    if not scenarios:
        raise ValueError(f"No scenarios matched for pack {pack_slug}")
    rubric = pack_path(pack, "judge_rubric").read_text(encoding="utf-8")
    skill_prompt_path = prompt_file or pack_path(pack, "skill_prompt")
    skill_prompt = skill_prompt_path.read_text(encoding="utf-8")
    client = _make_client()
    coach_model = os.environ.get("EVAL_COACH_MODEL", "gpt-4.1-mini")
    judge_model = os.environ.get("EVAL_JUDGE_MODEL", "gpt-4.1-mini")

    rows = []
    for scenario in scenarios:
        assembled = build_skill_input(pack, scenario, skill_prompt)
        coach_response, latency_ms = _chat_text(
            client,
            model=coach_model,
            system="You are the EOL Daily Coach. Follow the active skill prompt and tool contract.",
            user=assembled,
        )
        judge_prompt = build_judge_prompt(pack, scenario, rubric, coach_response)
        judge_text, _judge_latency_ms = _chat_text(
            client,
            model=judge_model,
            system="You are a strict JSON-only evaluator.",
            user=judge_prompt,
        )
        judge = _extract_json_object(judge_text)
        judge["sqs"] = recompute_sqs(judge, pack)
        rows.append(
            {
                "scenario_id": scenario["id"],
                "pack_slug": pack["slug"],
                "skill_id": pack["id"],
                "sqs": judge["sqs"],
                "latency_ms": round(latency_ms, 1),
                "coach_response": coach_response,
                "judge": judge,
            }
        )

    result = {
        "pack_slug": pack["slug"],
        "skill_id": pack["id"],
        "mean_sqs": round(sum(row["sqs"] for row in rows) / len(rows), 2) if rows else 0.0,
        "per_scenario": rows,
    }
    if output_json:
        write_json(output_json, result)
    return result


def print_assembled_input(pack_slug: str, scenario_id: str | None = None, prompt_file: Path | None = None) -> str:
    pack = load_pack(ROOT, pack_slug)
    scenarios = select_scenarios(load_pack_scenarios(pack), scenario_id=scenario_id, max_count=1)
    if not scenarios:
        raise ValueError(f"No scenarios matched for pack {pack_slug}")
    prompt_path = prompt_file or pack_path(pack, "skill_prompt")
    return build_skill_input(pack, scenarios[0], prompt_path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", default=DEFAULT_PACK_SLUG)
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--scenario-id")
    parser.add_argument("--max", type=int, dest="max_count")
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--print-assembled-input", action="store_true")
    args = parser.parse_args()

    if args.print_assembled_input:
        print(print_assembled_input(args.pack, scenario_id=args.scenario_id, prompt_file=args.prompt_file))
        return 0

    result = run_eval(
        pack_slug=args.pack,
        prompt_file=args.prompt_file,
        scenario_id=args.scenario_id,
        max_count=args.max_count,
        output_json=args.output_json,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
