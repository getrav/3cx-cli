from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from shutil import copytree


class TestSkillArtifacts(unittest.TestCase):
    def test_validator_accepts_skill_artifacts(self) -> None:
        repo_root = Path(__file__).resolve().parent
        validator = (
            repo_root
            / ".agents"
            / "skills"
            / "3cx-pbx-cli"
            / "scripts"
            / "validate-skill.py"
        )

        result = subprocess.run(
            ["python3", str(validator)],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(
            result.returncode,
            0,
            msg=f"validator stdout:\n{result.stdout}\nvalidator stderr:\n{result.stderr}",
        )
        self.assertNotIn("verification skipped", result.stdout)

    def test_validator_accepts_installed_skill_without_repository(self) -> None:
        repo_root = Path(__file__).resolve().parent
        source_skill = repo_root / ".agents" / "skills" / "3cx-pbx-cli"

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            installed_skill = temporary_root / ".agents" / "skills" / "3cx-pbx-cli"
            copytree(source_skill, installed_skill)
            validator = installed_skill / "scripts" / "validate-skill.py"

            result = subprocess.run(
                ["python3", str(validator)],
                cwd=temporary_root,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(
            result.returncode,
            0,
            msg=f"validator stdout:\n{result.stdout}\nvalidator stderr:\n{result.stderr}",
        )
        self.assertIn("dynamic command-source verification skipped", result.stdout)


if __name__ == "__main__":
    unittest.main()
