# EOL Skill Optimizer

Small pack-based optimizer for Experiment of Life Daily Coach skills.

Each specialist skill owns its own eval pack: prompt, scenarios, judge rubric, mutation notes, and results. This repo does not change the EOL app automatically.

Current packs:

- `task_initiation` - reviewed and mutation-enabled
- `emotional_regulation` - drafted for review, mutation disabled
- `day_scheduling` - drafted for review, mutation disabled
- `goal_experiment` - drafted for review, mutation disabled

## Layout

- `packs/<pack>/pack.json` configures a specialist skill pack.
- `packs/<pack>/skill.md` stores that pack's local baseline prompt.
- `packs/<pack>/scenarios.json` stores fixed scenarios for that skill.
- `packs/<pack>/judge_rubric.md` stores that skill's scoring rubric.
- `evals/eval_harness.py` assembles active skill context, prompt, history, and user message.
- `orchestrator.py` runs eval-only or one-candidate optimization for one pack or all mutation-enabled packs.

## Quick Start

```powershell
python -m pip install -r requirements.txt
python -m pytest tests
python evals/eval_harness.py --pack task_initiation --scenario-id vague_stuck_name_one_task --print-assembled-input
```

To run model-backed evals:

```powershell
Copy-Item .env.example .env
# Fill OPENAI_API_KEY in .env
python orchestrator.py --pack task_initiation --eval-only
```

Optimize one pack:

```powershell
python orchestrator.py --pack task_initiation --optimize
```

Optimize every enabled pack:

```powershell
python orchestrator.py --all-enabled --optimize
```

## Adding A Pack

1. Create `packs/<pack_slug>/`.
2. Add `pack.json`, `skill.md`, `scenarios.json`, `judge_rubric.md`, and `mutation_notes.md`.
3. Keep `mutation_enabled` false until you have reviewed the rubric and scenarios.
4. Run an eval-only baseline before allowing mutation.

Promotion is local to the pack's `skill.md`; syncing back to `Experiment-of-Life` is manual.
