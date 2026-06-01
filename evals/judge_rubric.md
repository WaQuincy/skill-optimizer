# Skill Quality Score Rubric

Score each dimension as an integer 1-5. Be strict: safe but generic is a 3.

Use this weighted formula:

`sqs = 0.20*activation_fit + 0.20*conversation_control + 0.20*tiny_next_action + 0.15*tone + 0.15*handoff_behavior + 0.10*state_update_contract`

## Dimensions

- `activation_fit`: The response respects whether the active skill should own this turn.
- `conversation_control`: The response asks at most one question and advances the skill without bloating the interaction.
- `tiny_next_action`: The response reduces stuckness into a concrete 2-10 minute action when appropriate.
- `tone`: The response is validating, non-shaming, warm, and concise.
- `handoff_behavior`: The response hands off or cancels when the user asks for unrelated work.
- `state_update_contract`: The response uses the expected `skill_update` status/phase behavior for the scenario.

If a scenario anti-pattern appears, cap the relevant dimension at 2.

Return only JSON:

```json
{
  "activation_fit": 1,
  "conversation_control": 1,
  "tiny_next_action": 1,
  "tone": 1,
  "handoff_behavior": 1,
  "state_update_contract": 1,
  "sqs": 1.0,
  "notes": "one short sentence under 200 characters"
}
```

