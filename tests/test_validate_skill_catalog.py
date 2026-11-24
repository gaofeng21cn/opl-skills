from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_skill_catalog",
    ROOT / "scripts/validate_skill_catalog.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SkillCatalogValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = MODULE.load()

    def test_current_catalog_is_valid(self) -> None:
        self.assertEqual(MODULE.validate(self.catalog), [])

    def test_catalog_contains_only_current_source_skills(self) -> None:
        source_ids = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual(set(self.catalog["skills"]), source_ids)

    def test_source_path_must_bind_skill_id(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        catalog["skills"]["academic-defense-prep"]["source_path"] = "skills/other"
        self.assertIn(
            "academic-defense-prep: source_path must bind the Skill ID",
            MODULE.validate(catalog),
        )

    def test_unclassified_source_skill_is_rejected(self) -> None:
        catalog = copy.deepcopy(self.catalog)
        del catalog["skills"]["academic-defense-prep"]
        self.assertTrue(any("catalog differs from source" in error for error in MODULE.validate(catalog)))

    def test_validate_skills_frontmatter_handles_pyyaml_and_stdlib_fallback(self) -> None:
        spec = importlib.util.spec_from_file_location("validate_skills", ROOT / "scripts/validate_skills.py")
        assert spec and spec.loader
        validate_skills = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(validate_skills)

        sample = '---\nname: sample-skill\ndescription: "Use when: testing quotes"\n---\n# Body\n'
        self.assertEqual(
            validate_skills.parse_frontmatter(sample),
            {"name": "sample-skill", "description": "Use when: testing quotes"},
        )
        original_yaml = validate_skills.yaml
        try:
            validate_skills.yaml = None
            self.assertEqual(
                validate_skills.parse_frontmatter(sample),
                {"name": "sample-skill", "description": "Use when: testing quotes"},
            )
        finally:
            validate_skills.yaml = original_yaml


if __name__ == "__main__":
    unittest.main()
