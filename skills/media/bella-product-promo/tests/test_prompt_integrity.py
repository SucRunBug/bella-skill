"""Check vendored prompt bytes and indexes without the upstream checkout."""

import hashlib
import json
from pathlib import Path
import re
import unittest
from urllib.parse import urlparse


SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCES = SKILL_ROOT / "references"
ORIGINALS = REFERENCES / "original-prompts"
UPSTREAM_COMMIT = "92aee2f586ac0715cb3cbcb6384834f98a33383d"
UPSTREAM_BASE = "https://github.com/yihui-dev/awesome-opus5-5-videos"
EXPECTED_HASHES = {
    "brainextends-606193": "68bce1759b2b9838f1ddc72a5e76320d13adecf735acff9bf5ecb2a70863ae7d",
    "annacher-433425": "5b71ca519a48f8da539f734ad2948640b77f6ba4311dcde8ccb227ceb14bf475",
    "howdevelop-733090": "3ca30e013d3808ca973526192fa018d1ccb46fbbd8b980d8bf0bd01264090be3",
    "ho-ba-761062": "65201304be23dfc46d996ad61b1ee378e4ce204824a60699b2cc670be09ef03b",
    "jhylee95-452427": "85a03a501e6c2cf729906c72ceca4895de92c07a4c035ed9f54c7511a4206277",
    "twoclipping-496100": "ecb8efb69c7c27dae518790937d665cc15b4d904fd1337433db76289c889a4aa",
    "twoclipping-000267": "0600067aed88a2a398418036336956fcaa924bfaa7b6a60e8bb5f550f0f1af2d",
    "moritzkremb-466494": "0d49d231a3ce23e2ad3ce4196123f7c0c619cff0194f26e5b91b497e62ab54f3",
    "techtactician-144474": "86994185c472363ebb88e2ef85000110efae76eb61333ebc6ffc7ca8b281bf16",
    "twoclipping-747965": "205f3c0bff72b24f0bb429da97da27113b7ad681e43d66e6c02e7c7733f4815e",
    "0xnicc0-516612": "9f3f269032749021fa71b8cf895197db40bf6e7f5669edb5d21fddb5384df9d0",
    "twoclipping-762046": "8e69e140f902b70b63f8e85b09c89e37d5971aa8313df3f21f4fa86065ef80f6",
}
EXPECTED_STYLES = {
    "spotify-premium", "minimal-ui", "tech-launch", "real-ui", "social-launch",
    "apple-continuous", "footage-hybrid", "outcome-story", "shape-morph",
}
TECH_CHOICES = {"native-html", "gsap", "remotion", "threejs", "blender", "hybrid"}
LICENSE_HASH = "0adca04960d4c36b2524d26a400b790c28e583ce019635ab2d3a9ba3dc9dda7f"


class PromptIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.presets = json.loads((REFERENCES / "presets.json").read_text(encoding="utf-8"))
        cls.sources = cls.presets["sources"]
        cls.styles = cls.presets["styles"]

    def test_originals_are_exact_snapshot_bytes(self):
        self.assertEqual(
            {path.name for path in ORIGINALS.iterdir()},
            {f"{slug}.md" for slug in EXPECTED_HASHES} | {"LICENSE"},
        )
        for slug, expected in EXPECTED_HASHES.items():
            with self.subTest(slug=slug):
                self.assertEqual(
                    hashlib.sha256((ORIGINALS / f"{slug}.md").read_bytes()).hexdigest(),
                    expected,
                )
        self.assertEqual(hashlib.sha256((ORIGINALS / "LICENSE").read_bytes()).hexdigest(), LICENSE_HASH)

    def test_source_manifest_preserves_all_origins(self):
        slugs = [source["slug"] for source in self.sources]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(set(slugs), set(EXPECTED_HASHES))
        for source in self.sources:
            slug = source["slug"]
            with self.subTest(slug=slug):
                self.assertEqual(source["file"], f"original-prompts/{slug}.md")
                self.assertEqual(source["sha256"], EXPECTED_HASHES[slug])
                self.assertEqual(source["upstream_commit"], UPSTREAM_COMMIT)
                self.assertEqual(
                    source["upstream_url"],
                    f"{UPSTREAM_BASE}/blob/{UPSTREAM_COMMIT}/prompts/{slug}.md",
                )
                original = (REFERENCES / source["file"]).read_text(encoding="utf-8")
                self.assertIn(source["post_url"], original)
                self.assertEqual(urlparse(source["post_url"]).hostname, "x.com")
                if source["has_remake"]:
                    self.assertIn(source["skillry_url"], original)
                    self.assertEqual(urlparse(source["skillry_url"]).hostname, "skillry.dev")
                else:
                    self.assertIsNone(source["skillry_url"])
                self.assertFalse(source["prompt_partial"])
                self.assertIn(source["source_kind"], {"specific_task", "input_template", "open_brief"})
                self.assertTrue(set(source["original_tech_requirements"]) <= TECH_CHOICES)
                self.assertIsInstance(source["remake_tech_tags"], list)
                self.assertTrue(source["asset_dependencies"])
                self.assertTrue(source["notes"])

    def test_style_and_prompt_indexes_have_no_missing_or_orphan_entries(self):
        self.assertEqual(self.presets["schema_version"], 1)
        style_ids = [style["id"] for style in self.styles]
        self.assertEqual(len(style_ids), len(set(style_ids)))
        self.assertEqual(set(style_ids), EXPECTED_STYLES)
        sources = {source["slug"]: source for source in self.sources}
        referenced = set()
        for style in self.styles:
            with self.subTest(style=style["id"]):
                for field in ("title", "description", "best_for", "reference_slugs", "suggested_tech", "needs", "notes"):
                    self.assertTrue(style[field], f"Empty style field: {field}")
                self.assertEqual(len(style["reference_slugs"]), len(set(style["reference_slugs"])))
                self.assertTrue(set(style["suggested_tech"]) <= TECH_CHOICES)
                for slug in style["reference_slugs"]:
                    self.assertIn(slug, sources)
                    self.assertIn(style["id"], sources[slug]["style_ids"])
                    referenced.add(slug)
        self.assertEqual(referenced, set(EXPECTED_HASHES))
        by_style = {style["id"]: style for style in self.styles}
        library = (REFERENCES / "prompt-library.md").read_text(encoding="utf-8")
        for slug, source in sources.items():
            self.assertIn(source["file"], library)
            self.assertTrue(source["style_ids"])
            for style_id in source["style_ids"]:
                self.assertIn(style_id, by_style)
                self.assertIn(slug, by_style[style_id]["reference_slugs"])
            duration = source["original_duration"]
            self.assertIn(duration["kind"], {"exact", "beat_derived", "unspecified"})
            if duration["kind"] == "unspecified":
                self.assertIsNone(duration["seconds"])
            else:
                self.assertGreater(duration["seconds"], 0)
            self.assertTrue(duration["detail"])

    def test_reference_links_resolve_without_source_checkout(self):
        for guide in (REFERENCES / "prompt-library.md", REFERENCES / "provenance.md"):
            text = guide.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if urlparse(target).scheme or target.startswith("#"):
                    continue
                path = guide.parent / target.split("#", 1)[0]
                with self.subTest(guide=guide.name, target=target):
                    self.assertTrue(path.is_file())
                    self.assertIn(REFERENCES.resolve(), path.resolve().parents)

    def test_package_has_no_personal_absolute_paths(self):
        unix_personal = re.compile(r"/(?:Users|home)/[A-Za-z0-9_.-]+")
        windows_personal = re.compile(r"\b[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9_.-]+")
        for path in SKILL_ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".json", ".py", ".yaml", ".yml"}:
                continue
            with self.subTest(file=path.relative_to(SKILL_ROOT).as_posix()):
                text = path.read_text(encoding="utf-8")
                self.assertIsNone(unix_personal.search(text))
                self.assertIsNone(windows_personal.search(text))


if __name__ == "__main__":
    unittest.main()
