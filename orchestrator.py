#!/usr/bin/env python3
"""Tiny one-candidate optimizer for skill prompts."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from evals.eval_harness import ROOT, load_skill_registry, run_eval, write_json

RESULTS_DIR = ROOT / "results"
EXPERIMENTS_DIR = RESULTS_DIR / "experiments"
SUMMARIES_DIR = RESULTS_DIR / "summaries"
PROGRAM_PATH = ROOT / "program.md"
CHALLENGER_PREVIEW_PATH = ROOT / "prompts" / "challenger_preview.md"


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _make_client():
    from openai import OpenAI

    base_url = os.environ.get("OPENAI_BASE_URL") or None
    kwargs: dict[str, Any] = {"api_key": os.environ["OPENAI_API_KEY"]}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def generate_candidate(skill_prompt: str, baseline_result: dict[str, Any]) -> str:
    load_dotenv(ROOT / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for candidate generation")
    client = _make_client()
    model = os.environ.get("MUTATION_MODEL", "gpt-4.1-mini")
    strategy = PROGRAM_PATH.read_text(encoding="utf-8")
    weak_rows = sorted(baseline_result.get("per_scenario") or [], key=lambda row: float(row.get("sqs", 0)))[:3]
    prompt = f"""Improve this EOL Daily Coach skill prompt.

Return only the full replacement skill.md content. Do not explain.

Mutation strategy:
{strategy}

Lowest-scoring scenarios:
{json.dumps(weak_rows, indent=2, ensure_ascii=False)[:5000]}

Current skill prompt:
{skill_prompt}
"""
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You conservatively improve skill.md prompts."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.35,
    )
    candidate = (response.choices[0].message.content or "").strip()
    if not candidate.startswith("#"):
        raise RuntimeError("Candidate did not look like a full markdown skill prompt")
    return candidate


def write_summary(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Skill Optimizer Run",
        "",
        f"- mode: {result['mode']}",
        f"- skill_id: {result['skill_id']}",
        f"- baseline_mean_sqs: {result['baseline']['mean_sqs']}",
    ]
    if result.get("candidate"):
        lines.extend(
            [
                f"- candidate_mean_sqs: {result['candidate']['mean_sqs']}",
                f"- promoted: {result['promoted']}",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-only", action="store_true")
    parser.add_argument("--skill-id", default="daily.overcome_procrastination")
    parser.add_argument("--promote", action="store_true", help="Replace the local skill baseline if gates pass.")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    registry = {skill["id"]: skill for skill in load_skill_registry(ROOT)}
    if args.skill_id not in registry:
        raise SystemExit(f"Unknown skill id: {args.skill_id}")

    skill_path = ROOT / registry[args.skill_id]["prompt_path"]
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    baseline = run_eval(prompt_file=skill_path, skill_id=args.skill_id)
    result: dict[str, Any] = {
        "mode": "eval-only" if args.eval_only else "optimize",
        "skill_id": args.skill_id,
        "baseline": baseline,
        "candidate": None,
        "promoted": False,
    }

    if not args.eval_only:
        candidate = generate_candidate(skill_path.read_text(encoding="utf-8"), baseline)
        CHALLENGER_PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
        CHALLENGER_PREVIEW_PATH.write_text(candidate + "\n", encoding="utf-8")
        candidate_result = run_eval(prompt_file=CHALLENGER_PREVIEW_PATH, skill_id=args.skill_id)
        result["candidate"] = candidate_result
        margin = _env_float("PROMOTION_MARGIN", 0.10)
        improves = candidate_result["mean_sqs"] >= baseline["mean_sqs"] + margin
        if args.promote and improves:
            shutil.copyfile(CHALLENGER_PREVIEW_PATH, skill_path)
            result["promoted"] = True

    experiment_path = EXPERIMENTS_DIR / f"skill-opt-{stamp}.json"
    summary_path = SUMMARIES_DIR / f"skill-opt-{stamp}.md"
    write_json(experiment_path, result)
    write_summary(summary_path, result)
    print(f"Wrote {experiment_path}")
    print(f"Wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
