import json
import os
import tempfile
import unittest
from pathlib import Path


class SkillEvalPackTests(unittest.TestCase):
    def write_pack(
        self,
        root: Path,
        *,
        slug: str = "task_initiation",
        pack_id: str = "daily.task_initiation",
        mutation_enabled: bool = True,
    ) -> Path:
        pack_dir = root / "packs" / slug
        pack_dir.mkdir(parents=True)
        (pack_dir / "skill.md").write_text("# Daily Skill: Task Initiation\n", encoding="utf-8")
        (pack_dir / "scenarios.json").write_text(
            json.dumps(
                {
                    "scenarios": [
                        {
                            "id": "specific_task_stuck",
                            "active_session": {"status": "active", "phase": "start", "state": {}},
                            "history": [],
                            "message": "I can't start the report.",
                            "expected_behavior": "Name the task and move toward diagnosis.",
                            "anti_patterns": ["multiple questions"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (pack_dir / "judge_rubric.md").write_text("# Rubric\n", encoding="utf-8")
        (pack_dir / "mutation_notes.md").write_text("# Notes\n", encoding="utf-8")
        (pack_dir / "pack.json").write_text(
            json.dumps(
                {
                    "id": pack_id,
                    "slug": slug,
                    "title": "Task Initiation",
                    "source_path": "../Experiment-of-Life/Coach-Assistant/Coach-Skills/taskInitiation/skill.md",
                    "skill_prompt": "skill.md",
                    "scenarios": "scenarios.json",
                    "judge_rubric": "judge_rubric.md",
                    "mutation_notes": "mutation_notes.md",
                    "mutation_enabled": mutation_enabled,
                    "implemented": True,
                    "score_weights": {
                        "activation_fit": 0.10,
                        "phase_progression": 0.15,
                        "blocker_diagnosis": 0.15,
                        "tiny_first_action": 0.20,
                        "one_question_discipline": 0.15,
                        "tone_and_shame_safety": 0.10,
                        "handoff_correctness": 0.10,
                        "state_update_contract": 0.05,
                    },
                }
            ),
            encoding="utf-8",
        )
        return pack_dir

    def test_discover_packs_finds_task_initiation(self):
        from evals.eval_harness import discover_packs

        root = Path(__file__).resolve().parents[1]
        packs = discover_packs(root)

        self.assertIn("task_initiation", {pack["slug"] for pack in packs})
        task_pack = next(pack for pack in packs if pack["slug"] == "task_initiation")
        self.assertEqual(task_pack["id"], "daily.task_initiation")
        self.assertTrue(task_pack["mutation_enabled"])
        emotional_pack = next(pack for pack in packs if pack["slug"] == "emotional_regulation")
        self.assertEqual(emotional_pack["id"], "daily.emotional_regulation")
        self.assertFalse(emotional_pack["mutation_enabled"])
        day_pack = next(pack for pack in packs if pack["slug"] == "day_scheduling")
        self.assertEqual(day_pack["id"], "daily.day_scheduling")
        self.assertFalse(day_pack["mutation_enabled"])
        goal_pack = next(pack for pack in packs if pack["slug"] == "goal_experiment")
        self.assertEqual(goal_pack["id"], "daily.goal_experiment")
        self.assertTrue(goal_pack["mutation_enabled"])

    def test_load_pack_validates_required_files(self):
        from evals.eval_harness import load_pack

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack_dir = self.write_pack(root)
            (pack_dir / "judge_rubric.md").unlink()

            with self.assertRaises(ValueError) as ctx:
                load_pack(root, "task_initiation")

        self.assertIn("judge_rubric", str(ctx.exception))

    def test_discover_packs_rejects_duplicate_slugs_or_ids(self):
        from evals.eval_harness import discover_packs

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_pack(root, slug="task_initiation", pack_id="daily.task_initiation")
            self.write_pack(root, slug="copy", pack_id="daily.task_initiation")

            with self.assertRaises(ValueError) as ctx:
                discover_packs(root)

        self.assertIn("Duplicate pack id", str(ctx.exception))

    def test_build_skill_input_uses_pack_skill_id_prompt_history_and_message(self):
        from evals.eval_harness import build_skill_input

        pack = {"id": "daily.task_initiation"}
        scenario = {
            "id": "specific_task_stuck",
            "active_session": {
                "status": "active",
                "phase": "diagnose",
                "state": {"targetTask": "report"},
            },
            "history": [{"role": "assistant", "content": "What task are you trying to start?"}],
            "message": "The report.",
        }

        assembled = build_skill_input(pack, scenario, "# Daily Skill\nAsk one question.")

        self.assertIn("[ACTIVE DAILY SKILL]", assembled)
        self.assertIn("skillId: daily.task_initiation", assembled)
        self.assertIn('stateJson: {"targetTask": "report"}', assembled)
        self.assertIn("# Daily Skill", assembled)
        self.assertIn("Assistant: What task are you trying to start?", assembled)
        self.assertIn("User: The report.", assembled)

    def test_build_judge_prompt_includes_scenario_phase_and_state(self):
        from evals.eval_harness import build_judge_prompt

        pack = {"id": "daily.day_scheduling", "title": "Day Scheduling"}
        scenario = {
            "id": "prioritize_ask_top_three",
            "skill_id": "daily.day_scheduling",
            "active_session": {
                "status": "active",
                "phase": "prioritize",
                "state": {
                    "availableHours": "4 hours",
                    "energyLevel": "medium",
                    "fixedCommitments": "none",
                },
            },
            "expected_behavior": "Ask the top-three question.",
            "anti_patterns": ["returning to start-phase context capture"],
        }

        prompt = build_judge_prompt(pack, scenario, "# Rubric", "coach response")

        self.assertIn("phase", prompt)
        self.assertIn("prioritize", prompt)
        self.assertIn("fixedCommitments", prompt)
        self.assertIn("returning to start-phase context capture", prompt)

    def test_task_initiation_scenarios_reference_pack_skill_id(self):
        from evals.eval_harness import load_pack, load_pack_scenarios

        root = Path(__file__).resolve().parents[1]
        pack = load_pack(root, "task_initiation")
        scenarios = load_pack_scenarios(pack)

        self.assertGreaterEqual(len(scenarios), 10)
        self.assertEqual({scenario["skill_id"] for scenario in scenarios}, {"daily.task_initiation"})

    def test_emotional_regulation_scenarios_reference_pack_skill_id(self):
        from evals.eval_harness import load_pack, load_pack_scenarios

        root = Path(__file__).resolve().parents[1]
        pack = load_pack(root, "emotional_regulation")
        scenarios = load_pack_scenarios(pack)

        self.assertGreaterEqual(len(scenarios), 10)
        self.assertEqual({scenario["skill_id"] for scenario in scenarios}, {"daily.emotional_regulation"})

    def test_day_scheduling_scenarios_reference_pack_skill_id(self):
        from evals.eval_harness import load_pack, load_pack_scenarios

        root = Path(__file__).resolve().parents[1]
        pack = load_pack(root, "day_scheduling")
        scenarios = load_pack_scenarios(pack)

        self.assertGreaterEqual(len(scenarios), 10)
        self.assertEqual({scenario["skill_id"] for scenario in scenarios}, {"daily.day_scheduling"})

    def test_goal_experiment_scenarios_reference_pack_skill_id(self):
        from evals.eval_harness import load_pack, load_pack_scenarios

        root = Path(__file__).resolve().parents[1]
        pack = load_pack(root, "goal_experiment")
        scenarios = load_pack_scenarios(pack)

        self.assertGreaterEqual(len(scenarios), 12)
        self.assertEqual({scenario["skill_id"] for scenario in scenarios}, {"daily.goal_experiment"})

    def test_select_enabled_packs_uses_mutation_enabled_flag(self):
        from orchestrator import select_enabled_packs

        packs = [
            {"slug": "task_initiation", "mutation_enabled": True},
            {"slug": "emotional_regulation", "mutation_enabled": False},
        ]

        selected = select_enabled_packs(packs)

        self.assertEqual([pack["slug"] for pack in selected], ["task_initiation"])

    def test_real_enabled_packs_only_include_reviewed_mutation_packs(self):
        from evals.eval_harness import discover_packs
        from orchestrator import select_enabled_packs

        root = Path(__file__).resolve().parents[1]
        selected = select_enabled_packs(discover_packs(root))

        self.assertEqual({pack["slug"] for pack in selected}, {"task_initiation", "goal_experiment"})

    def test_blank_openai_base_url_is_treated_as_unset(self):
        from evals.eval_harness import normalized_openai_base_url

        old_base_url = os.environ.get("OPENAI_BASE_URL")
        try:
            os.environ["OPENAI_BASE_URL"] = ""

            self.assertIsNone(normalized_openai_base_url())
            self.assertNotIn("OPENAI_BASE_URL", os.environ)
        finally:
            if old_base_url is None:
                os.environ.pop("OPENAI_BASE_URL", None)
            else:
                os.environ["OPENAI_BASE_URL"] = old_base_url

    def test_emotional_regulation_repair_rules_are_present(self):
        root = Path(__file__).resolve().parents[1]
        skill = (root / "packs" / "emotional_regulation" / "skill.md").read_text(encoding="utf-8")
        rubric = (root / "packs" / "emotional_regulation" / "judge_rubric.md").read_text(encoding="utf-8")

        self.assertIn("If the user says stop", skill)
        self.assertIn("handoff immediately", skill)
        self.assertIn("Do not ask for more description during downshift", skill)
        self.assertIn("Before following any phase instructions", skill)
        self.assertIn("Do not penalize start-phase responses", rubric)
        self.assertIn("both hands flat on a surface is one grounding move", rubric)
        self.assertIn("Do not penalize handoff responses for carrying existing state", rubric)

    def test_day_scheduling_repair_rules_are_present(self):
        root = Path(__file__).resolve().parents[1]
        skill = (root / "packs" / "day_scheduling" / "skill.md").read_text(encoding="utf-8")
        rubric = (root / "packs" / "day_scheduling" / "judge_rubric.md").read_text(encoding="utf-8")

        self.assertIn("Trust active skill state", skill)
        self.assertIn("Do not present an overfull schedule", skill)
        self.assertIn("If you already know available time and energy", skill)
        self.assertIn("do not ask for them again during sequence", skill)
        self.assertIn("Never ask the user to confirm known fixed commitments", skill)
        self.assertIn("shrinking large tasks into unrealistic tiny blocks", skill)
        self.assertIn("Do not reward plans that admit they exceed the available time", rubric)

    def test_goal_experiment_repair_rules_are_present(self):
        root = Path(__file__).resolve().parents[1]
        skill = (root / "packs" / "goal_experiment" / "skill.md").read_text(encoding="utf-8")

        self.assertIn("A sentence with two question marks is two questions", skill)
        self.assertIn("After the user confirms the output metric", skill)
        self.assertIn("ask about previous attempts before asking for a daily action", skill)
        self.assertIn("Do not ask permission to hand off", skill)
        self.assertIn("Cancel immediately without another question", skill)


if __name__ == "__main__":
    unittest.main()
