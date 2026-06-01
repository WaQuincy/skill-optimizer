# EOL Skill Optimizer

Small multi-skill optimizer skeleton for Experiment of Life Daily Coach skills.

This repo evaluates and improves standalone `skill.md` prompts. It does not change the EOL app automatically.

## Layout

- `skills/registry.json` lists supported skills.
- `skills/<skill-id>/skill.md` stores each local baseline skill prompt.
- `evals/scenarios.json` stores fixed skill scenarios.
- `evals/eval_harness.py` assembles active skill context, prompt, history, and user message.
- `orchestrator.py` runs a simple one-candidate optimization loop.

## Quick Start

```powershell
python -m pip install -r requirements.txt
python -m pytest tests
python evals/eval_harness.py --scenario-id stuck_start --print-assembled-input
```

To run model-backed evals:

```powershell
Copy-Item .env.example .env
# Fill OPENAI_API_KEY in .env
python orchestrator.py --eval-only
```

## Adding A Skill

1. Create `skills/<skill-id>/skill.md`.
2. Add the skill to `skills/registry.json`.
3. Add scenarios in `evals/scenarios.json`.
4. Add scenario IDs to `evals/eval_config.json`.

Keep scenarios focused on skill behavior: activation fit, one-question discipline, state updates, handoff, and the quality of the next coaching move.

