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
CATALOG = json.loads((MAIN / "references/catalog.json").read_text(encoding="utf-8"))["skills"]
MEMBER_NAMES = {entry["name"] for entry in CATALOG}


class DiscoveryTests(unittest.TestCase):
    def test_source_checkout_discovers_catalog_members(self):
        rows = discovery.discover(MAIN)
        self.assertEqual(len(rows), len(CATALOG))
        self.assertEqual({row["name"] for row in rows}, MEMBER_NAMES)
        self.assertEqual(len(rows), len({row["name"] for row in rows}))
        self.assertTrue(all(row["status"] == "available" for row in rows))
        self.assertTrue(all(Path(row["skill_file"]).is_file() for row in rows))

    def test_category_limits_candidates(self):
        for category in {entry["category"] for entry in CATALOG}:
            with self.subTest(category=category):
                rows = discovery.discover(MAIN, category)
                expected = {entry["name"] for entry in CATALOG if entry["category"] == category}
                self.assertEqual({row["name"] for row in rows}, expected)

    def test_music_mv_is_routed_in_media(self):
        row = next(row for row in discovery.discover(MAIN, "media") if row["name"] == "bella-music-mv")
        self.assertEqual(row["path"], "media/bella-music-mv")
        self.assertEqual(row["status"], "available")
        self.assertIn("音乐与歌词", row["handoff"])
        self.assertIn("MP4", row["handoff"])

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
            self.assertEqual({row["name"] for row in rows}, MEMBER_NAMES)
            self.assertTrue(all(row["status"] == "available" for row in rows))

    def test_categorized_install_discovers_all_members(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "bella-skill"
            shutil.copytree(MAIN, root)
            for entry in CATALOG:
                target = base / entry["path"]
                target.mkdir(parents=True)
                shutil.copy2(REPO / "skills" / entry["path"] / "SKILL.md", target / "SKILL.md")
            rows = discovery.discover(root)
            self.assertEqual({row["name"] for row in rows}, MEMBER_NAMES)
            self.assertTrue(all(row["status"] == "available" for row in rows))
            self.assertTrue(all(Path(row["skill_file"]).is_relative_to(base.resolve()) for row in rows))

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
