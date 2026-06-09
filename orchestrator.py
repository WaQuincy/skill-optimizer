#!/usr/bin/env python3
"""Tiny pack-based optimizer for skill prompts."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from evals.eval_harness import (
    DEFAULT_PACK_SLUG,
    ROOT,
    discover_packs,
    load_pack,
    normalized_openai_base_url,
    pack_path,
    run_eval,
    write_json,
)


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

    base_url = normalized_openai_base_url()
    kwargs: dict[str, Any] = {"api_key": os.environ["OPENAI_API_KEY"]}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def select_enabled_packs(packs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [pack for pack in packs if bool(pack.get("mutation_enabled"))]


def generate_candidate(pack: dict[str, Any], skill_prompt: str, baseline_result: dict[str, Any]) -> str:
    load_dotenv(ROOT / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for candidate generation")
    client = _make_client()
    model = os.environ.get("MUTATION_MODEL", "gpt-4.1-mini")
    mutation_notes = pack_path(pack, "mutation_notes").read_text(encoding="utf-8")
    weak_rows = sorted(baseline_result.get("per_scenario") or [], key=lambda row: float(row.get("sqs", 0)))[:3]
    prompt = f"""Improve this EOL Daily Coach skill prompt.

Return only the full replacement skill.md content. Do not explain.

Pack:
- title: {pack['title']}
- skill_id: {pack['id']}

Mutation notes:
{mutation_notes}

Lowest-scoring scenarios and judge notes:
{json.dumps(weak_rows, indent=2, ensure_ascii=False)[:6000]}

Hard constraints:
- Preserve the skill's markdown structure and specialist boundaries.
- Make conservative, targeted edits only.
- Do not add app capabilities, backend assumptions, or new tool contracts.
- Keep `skill_update` completion, handoff, and cancellation behavior explicit.

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


def pack_results_dir(pack: dict[str, Any], name: str) -> Path:
    return Path(str(pack["_pack_dir"])) / "results" / name


def write_summary(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# Skill Optimizer Run",
        "",
        f"- mode: {result['mode']}",
        f"- pack: {result['pack_slug']}",
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


def run_pack(pack: dict[str, Any], *, mode: str, promote: bool) -> dict[str, Any]:
    skill_path = pack_path(pack, "skill_prompt")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    baseline = run_eval(pack_slug=str(pack["slug"]), prompt_file=skill_path)
    result: dict[str, Any] = {
        "mode": mode,
        "pack_slug": pack["slug"],
        "skill_id": pack["id"],
        "baseline": baseline,
        "candidate": None,
        "promoted": False,
    }

    if mode == "optimize":
        candidate = generate_candidate(pack, skill_path.read_text(encoding="utf-8"), baseline)
        challenger_preview_path = Path(str(pack["_pack_dir"])) / "challenger_preview.md"
        challenger_preview_path.write_text(candidate + "\n", encoding="utf-8")
        candidate_result = run_eval(pack_slug=str(pack["slug"]), prompt_file=challenger_preview_path)
        result["candidate"] = candidate_result
        margin = _env_float("PROMOTION_MARGIN", 0.10)
        improves = candidate_result["mean_sqs"] >= baseline["mean_sqs"] + margin
        if promote and improves:
            shutil.copyfile(challenger_preview_path, skill_path)
            result["promoted"] = True

    experiment_path = pack_results_dir(pack, "experiments") / f"{pack['slug']}-{stamp}.json"
    summary_path = pack_results_dir(pack, "summaries") / f"{pack['slug']}-{stamp}.md"
    write_json(experiment_path, result)
    write_summary(summary_path, result)
    print(f"Wrote {experiment_path}")
    print(f"Wrote {summary_path}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", default=DEFAULT_PACK_SLUG)
    parser.add_argument("--all-enabled", action="store_true")
    parser.add_argument("--eval-only", action="store_true")
    parser.add_argument("--optimize", action="store_true")
    parser.add_argument("--promote", action="store_true", help="Replace the local pack skill baseline if gates pass.")
    args = parser.parse_args()

    if args.eval_only and args.optimize:
        raise SystemExit("Choose only one mode: --eval-only or --optimize")
    mode = "optimize" if args.optimize or not args.eval_only else "eval-only"

    load_dotenv(ROOT / ".env")
    if args.all_enabled:
        packs = select_enabled_packs(discover_packs(ROOT))
        if not packs:
            raise SystemExit("No mutation-enabled packs found")
    else:
        packs = [load_pack(ROOT, args.pack)]

    for pack in packs:
        run_pack(pack, mode=mode, promote=args.promote)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
