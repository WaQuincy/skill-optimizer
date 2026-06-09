# Goal Experiment Skill Quality Rubric

Score each dimension as an integer 1-5. Be strict: safe but generic is a 3.

Use the weighted formula from `pack.json`:

`sqs = 0.10*activation_fit + 0.17*phase_progression + 0.13*goal_clarity + 0.14*metric_design + 0.16*system_design_quality + 0.12*experiment_framing + 0.10*one_question_discipline + 0.05*handoff_or_cancel_safety + 0.03*state_update_contract`

## Dimensions

- `activation_fit`: The response respects Goal Experiment scope and hands off for day planning, active experiment check-ins, technical help, or unrelated work.
- `phase_progression`: The response makes the correct next move for the active phase without premature finalization or repeated questions.
- `goal_clarity`: The response clarifies the goal area, goal statement, and personal why without accepting vague obligation.
- `metric_design`: The response helps define observable output metrics and controllable input metrics without using technical language.
- `system_design_quality`: The response designs a tiny daily action/system that can survive hard days and reflects previous attempts.
- `experiment_framing`: The response frames the plan as a 2-week experiment and uses no-blame design-data language.
- `one_question_discipline`: The response asks at most one question and avoids compound interview-style turns.
- `handoff_or_cancel_safety`: The response hands off or cancels correctly for out-of-scope requests, existing experiment check-ins, or explicit stop.
- `state_update_contract`: The response uses the expected `skill_update` status, phase, and state behavior for the scenario.

## Anti-Patterns

If the response matches a scenario anti-pattern, cap the relevant dimension at 2. Major phase errors, premature completion, or missing required final state should score 1 or 2 for `phase_progression` and `state_update_contract`.

Phase-aware scoring notes:

- In `goal_definition`, the ideal response clarifies goal, personal why, or observable output metric. It should not design the daily action too early.
- In `system_design`, the ideal response uses previous-attempt context and moves toward one controllable daily input action.
- In `optimization`, the ideal response treats concerns as design iteration and refines or simplifies the system.
- In `completed`, the ideal response previews the full experiment, confirms or records start date, and completes only when start date is known.

## Judge Output

Return only JSON:

```json
{
  "activation_fit": 1,
  "phase_progression": 1,
  "goal_clarity": 1,
  "metric_design": 1,
  "system_design_quality": 1,
  "experiment_framing": 1,
  "one_question_discipline": 1,
  "handoff_or_cancel_safety": 1,
  "state_update_contract": 1,
  "sqs": 1.0,
  "notes": "one short sentence under 200 characters"
}
```

