# Skill Prompt Mutation Strategy

Prefer conservative, high-signal edits.

- Preserve the skill's purpose and ownership boundary.
- Improve the next conversational move, not the whole Daily Coach.
- Keep the response concise and regulating.
- Preserve one-question-per-turn discipline unless the skill explicitly requires otherwise.
- Use `skill_update` only when the scenario calls for continuing, completing, handing off, or cancelling the active skill.
- Do not add product capabilities, backend assumptions, or new tool contracts.
- Avoid overfitting to one scenario phrase; fix the reusable instruction.

