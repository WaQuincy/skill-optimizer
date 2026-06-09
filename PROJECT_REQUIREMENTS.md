# Skill Optimizer Requirements

## Purpose

This repo is a small prompt lab for improving Experiment of Life Daily Coach specialist skills.
It is intentionally simpler than `coach-optimizer` and `onboarding-coach-optimizer`.

## Pack Model

Each skill is optimized through an eval pack under `packs/<pack_slug>/`.
A pack owns:

- local baseline `skill.md`
- skill-specific scenarios
- skill-specific judge rubric
- mutation notes
- mutation enablement flag
- pack-local result artifacts

## Scope

- Support multiple Daily Coach skills through pack discovery.
- Evaluate one pack with `--pack <slug>`.
- Optimize all reviewed packs with `--all-enabled`.
- Keep unreviewed packs with `mutation_enabled: false`.
- Keep promotion local to this optimizer repo.
- Sync back to the EOL app only through an explicit manual step.

## Non-Goals For V1

- No scheduled optimization.
- No train/holdout split.
- No latency gates.
- No app smoke test.
- No automatic write-back into `Experiment-of-Life`.
- No multi-challenger search.

## Promotion Rule

A candidate can replace a local pack baseline when its mean Skill Quality Score improves by at least `PROMOTION_MARGIN`.
