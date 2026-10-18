"""Exercise installation layouts and real discovery failures without user files."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
MAIN = REPO / "skills/bella-skill"
spec = importlib.util.spec_from_file_location("discovery", MAIN / "scripts/list_skills.py")
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)


class DiscoveryTests(unittest.TestCase):
    def test_source_checkout_discovers_eight_unique_members(self):
        rows = discovery.discover(MAIN)
        self.assertEqual(len(rows), 8)
        self.assertEqual(len({row["name"] for row in rows}), 8)
        self.assertTrue(all(row["status"] == "available" for row in rows))
        self.assertTrue(all(Path(row["skill_file"]).is_file() for row in rows))

    def test_category_limits_candidates(self):
        rows = discovery.discover(MAIN, "english")
        self.assertEqual({row["name"] for row in rows}, {"bella-speaking-coach", "bella-audio-listening"})

    def flat_install(self, base):
        root = base / "bella-skill"
        shutil.copytree(MAIN, root)
        for entry in discovery.discover(MAIN):
            target = base / entry["name"]
            target.mkdir()
            shutil.copy2(entry["skill_file"], target / "SKILL.md")
        return root

    def test_flat_install_and_main_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = self.flat_install(base / "canonical")
            link = base / "agent-entry"
            link.symlink_to(root, target_is_directory=True)
            rows = discovery.discover(link)
            self.assertTrue(all(row["status"] == "available" for row in rows))

    def test_missing_member_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.flat_install(Path(tmp))
            shutil.rmtree(root.parent / "tripo-3d")
            row = next(row for row in discovery.discover(root) if row["name"] == "tripo-3d")
            self.assertEqual(row["status"], "missing")
            self.assertIsNone(row["skill_file"])

    def test_mismatched_name_is_not_routed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.flat_install(Path(tmp))
            (root.parent / "tripo-3d/SKILL.md").write_text("---\nname: other\ndescription: Wrong member\n---\n")
            row = next(row for row in discovery.discover(root) if row["name"] == "tripo-3d")
            self.assertEqual(row["status"], "conflict")
            self.assertIsNone(row["skill_file"])

    def test_installed_description_comes_from_actual_definition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.flat_install(Path(tmp))
            definition = root.parent / "tripo-3d/SKILL.md"
            definition.write_text('---\nname: tripo-3d\ndescription: "Installed version description"\n---\n')
            row = next(row for row in discovery.discover(root) if row["name"] == "tripo-3d")
            self.assertEqual(row["description"], "Installed version description")

    def test_two_different_definitions_are_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.flat_install(Path(tmp))
            categorized = root.parent / "game-3d/tripo-3d"
            categorized.mkdir(parents=True)
            (categorized / "SKILL.md").write_text('---\nname: tripo-3d\ndescription: Different version\n---\n')
            row = next(row for row in discovery.discover(root) if row["name"] == "tripo-3d")
            self.assertEqual(row["status"], "conflict")

    def test_catalog_cannot_escape_skill_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.flat_install(Path(tmp))
            file = root / "references/catalog.json"
            catalog = json.loads(file.read_text())
            catalog["skills"][0]["path"] = "../../outside/bella-speaking-coach"
            file.write_text(json.dumps(catalog))
            with self.assertRaises(ValueError):
                discovery.discover(root)


if __name__ == "__main__":
    unittest.main()
