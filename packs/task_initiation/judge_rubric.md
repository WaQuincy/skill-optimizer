# Task Initiation Skill Quality Rubric

Score each dimension as an integer 1-5. Be strict: safe but generic is a 3.

Use the weighted formula from `pack.json`:

`sqs = 0.10*activation_fit + 0.15*phase_progression + 0.15*blocker_diagnosis + 0.20*tiny_first_action + 0.15*one_question_discipline + 0.10*tone_and_shame_safety + 0.10*handoff_correctness + 0.05*state_update_contract`

## Dimensions

- `activation_fit`: The response respects Task Initiation scope and does not turn the moment into day planning, project review, or emotional regulation unless handoff is needed.
- `phase_progression`: The response advances the current phase correctly without skipping required commitment or lingering after enough information is known.
- `blocker_diagnosis`: The response identifies or tracks the correct blocker type: `too_big`, `too_boring`, `decision_paralysis`, or `emotional_flooding`.
- `tiny_first_action`: The response gives or preserves one concrete 2-10 minute first action matched to the blocker.
- `one_question_discipline`: The response asks at most one question and avoids compound questioning unless the phase explicitly allows a brief combined question.
- `tone_and_shame_safety`: The response is validating, concise, and never implies the user's character, willpower, or effort is the problem.
- `handoff_correctness`: The response hands off for emotional flooding or unrelated work, and does not hand off when Task Initiation should continue.
- `state_update_contract`: The response uses the expected `skill_update` status, phase, and state behavior for the scenario.

## Anti-Patterns

If the response matches a scenario anti-pattern, cap the relevant dimension at 2. Major scope or status errors should score 1 for `phase_progression`, `handoff_correctness`, or `state_update_contract`.

## Judge Output

Return only JSON:

```json
{
  "activation_fit": 1,
  "phase_progression": 1,
  "blocker_diagnosis": 1,
  "tiny_first_action": 1,
  "one_question_discipline": 1,
  "tone_and_shame_safety": 1,
  "handoff_correctness": 1,
  "state_update_contract": 1,
  "sqs": 1.0,
  "notes": "one short sentence under 200 characters"
}
```

