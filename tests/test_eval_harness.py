import json
import tempfile
import unittest
from pathlib import Path


class SkillEvalHarnessTests(unittest.TestCase):
    def test_load_skill_registry_requires_unique_ids_and_existing_prompts(self):
        from evals.eval_harness import load_skill_registry

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "skills" / "daily.overcome_procrastination").mkdir(parents=True)
            (root / "skills" / "daily.overcome_procrastination" / "skill.md").write_text(
                "# Daily Skill: Overcome Procrastination\n",
                encoding="utf-8",
            )
            (root / "skills" / "registry.json").write_text(
                json.dumps(
                    {
                        "skills": [
                            {
                                "id": "daily.overcome_procrastination",
                                "title": "Overcome Procrastination",
                                "description": "Help the user restart.",
                                "prompt_path": "skills/daily.overcome_procrastination/skill.md",
                                "implemented": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            registry = load_skill_registry(root)

        self.assertEqual(registry[0]["id"], "daily.overcome_procrastination")
        self.assertEqual(registry[0]["prompt_path"], "skills/daily.overcome_procrastination/skill.md")

    def test_build_skill_input_includes_active_skill_context_prompt_history_and_message(self):
        from evals.eval_harness import build_skill_input

        scenario = {
            "id": "stuck_start",
            "skill_id": "daily.overcome_procrastination",
            "active_session": {
                "status": "active",
                "phase": "start",
                "state": {"topic": "thesis draft"},
            },
            "history": [{"role": "assistant", "content": "What are you avoiding opening?"}],
            "message": "the thesis draft",
        }

        assembled = build_skill_input(scenario, "# Daily Skill\nAsk one question.")

        self.assertIn("[ACTIVE DAILY SKILL]", assembled)
        self.assertIn("skillId: daily.overcome_procrastination", assembled)
        self.assertIn('stateJson: {"topic": "thesis draft"}', assembled)
        self.assertIn("# Daily Skill", assembled)
        self.assertIn("Assistant: What are you avoiding opening?", assembled)
        self.assertIn("User: the thesis draft", assembled)

    def test_eval_config_references_existing_scenarios_and_skills(self):
        from evals.eval_harness import load_json

        root = Path(__file__).resolve().parents[1]
        registry = load_json(root / "skills" / "registry.json")
        config = load_json(root / "evals" / "eval_config.json")
        scenarios = load_json(root / "evals" / "scenarios.json")["scenarios"]

        skill_ids = {skill["id"] for skill in registry["skills"]}
        scenario_ids = {scenario["id"] for scenario in scenarios}
        referenced_ids = set(config["scenario_ids"])

        self.assertTrue(skill_ids)
        self.assertTrue(referenced_ids)
        self.assertEqual(referenced_ids - scenario_ids, set())
        self.assertEqual({scenario["skill_id"] for scenario in scenarios} - skill_ids, set())

    def test_select_scenarios_can_filter_by_skill_id(self):
        from evals.eval_harness import select_scenarios

        scenarios = [
            {"id": "a", "skill_id": "daily.overcome_procrastination"},
            {"id": "b", "skill_id": "daily.project_review"},
        ]
        config = {"scenario_ids": ["a", "b"]}

        selected = select_scenarios(scenarios, config, skill_id="daily.project_review")

        self.assertEqual([scenario["id"] for scenario in selected], ["b"])


if __name__ == "__main__":
    unittest.main()
