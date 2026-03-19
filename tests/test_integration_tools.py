import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from tests.tools.integration_sequence_writer import generate_sequence
from tests.tools.integration_test_orchestrator import run_sequence_file


class TestIntegrationTools(unittest.TestCase):
    def test_sequence_writer_generates_actions(self):
        sequence = generate_sequence(["mainMenu", "partyMembers"], "mainMenu")
        self.assertIn("actions", sequence)
        self.assertGreater(len(sequence["actions"]), 0)
        self.assertEqual(sequence["actions"][0]["type"], "open")

    def test_orchestrator_runs_basic_sequence(self):
        sequence = {
            "start_menu": "mainMenu",
            "actions": [
                {"type": "open", "menu": "mainMenu"},
                {"type": "select", "target": "partyMembers"},
                {"type": "back"},
                {"type": "assert_menu", "target": "mainMenu"},
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            sequence_path = Path(temp_dir) / "sequence.json"
            with open(sequence_path, "w", encoding="utf-8") as f:
                json.dump(sequence, f, indent=4)
            asyncio.run(run_sequence_file(str(sequence_path)))


if __name__ == "__main__":
    unittest.main()
