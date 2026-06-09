# Day Scheduling Skill Quality Rubric

Score each dimension as an integer 1-5. Be strict: safe but generic is a 3.

Use the weighted formula from `pack.json`:

`sqs = 0.10*activation_fit + 0.15*phase_progression + 0.12*context_capture + 0.12*priority_limit + 0.18*realistic_sequence + 0.10*transition_and_buffer + 0.10*one_question_discipline + 0.08*handoff_or_cancel_safety + 0.05*state_update_contract`

## Dimensions

- `activation_fit`: The response respects Day Scheduling scope and hands off for emotional flooding or a single stuck task.
- `phase_progression`: The response follows the current phase without jumping ahead or lingering.
- `context_capture`: The response captures or uses available hours, energy, and fixed commitments before planning tasks.
- `priority_limit`: The response keeps the plan to 3 or fewer priorities and helps cut when the user names more.
- `realistic_sequence`: The response proposes one ordered plan that fits the available time and energy.
- `transition_and_buffer`: The response accounts for transition time, out-the-door buffers, and fixed commitments.
- `one_question_discipline`: The response asks at most one question, except for the brief combined start-phase context question.
- `handoff_or_cancel_safety`: The response hands off or cancels correctly for shame, single-task initiation, unrelated work, or explicit stop.
- `state_update_contract`: The response uses the expected `skill_update` status, phase, and state behavior for the scenario.

## Anti-Patterns

If the response matches a scenario anti-pattern, cap the relevant dimension at 2. Plans that exceed available time should score 1 or 2 for `realistic_sequence` and `transition_and_buffer`.

Do not reward plans that admit they exceed the available time. If the response presents an overfull schedule before asking what to drop, score `realistic_sequence` and `transition_and_buffer` at 2 or lower.

Phase-aware scoring notes:

- In `phase: start`, a brief combined question about time, free hours, and fixed commitments is acceptable only when those facts are not already in state.
- If fixed commitments are already in active state, asking the user to confirm or relist them should reduce `context_capture` and `one_question_discipline`.
- In `phase: prioritize`, if available time and energy are already known, the ideal response asks the top-three question rather than returning to context capture.
- In `phase: sequence`, the ideal response trusts active state, respects fixed boundaries, includes transition buffers, and does not ask start-phase questions again.
- Re-asking for `availableHours`, `energyLevel`, `fixedCommitments`, or `topThree` when already present in active state should reduce `phase_progression` and `context_capture`.
- Compressing large tasks into unrealistic short blocks just to fit the available time should reduce `realistic_sequence` and `transition_and_buffer`.
- In `phase: commit`, the ideal response completes when the user confirms, or incorporates one adjustment and asks one confirm-again question.

## Judge Output

Return only JSON:

```json
{
  "activation_fit": 1,
  "phase_progression": 1,
  "context_capture": 1,
  "priority_limit": 1,
  "realistic_sequence": 1,
  "transition_and_buffer": 1,
  "one_question_discipline": 1,
  "handoff_or_cancel_safety": 1,
  "state_update_contract": 1,
  "sqs": 1.0,
  "notes": "one short sentence under 200 characters"
}
```
