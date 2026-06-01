# Skill Optimizer Requirements

## Purpose

This repo is a small prompt lab for improving Experiment of Life Daily Coach skill prompts.
It is intentionally simpler than `coach-optimizer` and `onboarding-coach-optimizer`.

## Scope

- Support multiple Daily Coach skills through `skills/registry.json`.
- Evaluate candidate `skill.md` files against fixed synthetic scenarios.
- Keep promotion local to this optimizer repo.
- Sync back to the EOL app only through an explicit manual step.

## Non-Goals For V1

- No scheduled optimization.
- No train/holdout split.
- No latency gates.
- No app smoke test.
- No automatic write-back into `experimentoflife`.
- No multi-challenger search.

## Promotion Rule

A candidate can replace a local skill baseline when its mean Skill Quality Score improves by at least `PROMOTION_MARGIN` and no scenario has a major contract failure.

