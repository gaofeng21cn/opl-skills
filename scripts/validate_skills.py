#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter opening delimiter")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("missing YAML frontmatter closing delimiter")
    block = text[4:end]
    data: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"').strip("'")
        data[key.strip()] = value
    return data


def validate_skill_dir(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir.name}: missing SKILL.md"]
    data = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    name = data.get("name", "")
    description = data.get("description", "")
    if not name:
        errors.append(f"{skill_dir.name}: frontmatter missing name")
    elif not NAME_PATTERN.match(name):
        errors.append(f"{skill_dir.name}: invalid name '{name}'")
    if not description:
        errors.append(f"{skill_dir.name}: frontmatter missing description")
    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    skills_dir = repo_root / "skills"
    if not skills_dir.is_dir():
        print("missing skills directory", file=sys.stderr)
        return 1
    errors: list[str] = []
    skill_dirs = sorted(path for path in skills_dir.iterdir() if path.is_dir())
    if not skill_dirs:
        print("no skills found", file=sys.stderr)
        return 1
    for skill_dir in skill_dirs:
        try:
            errors.extend(validate_skill_dir(skill_dir))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{skill_dir.name}: validation crashed: {exc}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    catalog = subprocess.run(
        [sys.executable, str(repo_root / "scripts/validate_skill_catalog.py")],
        cwd=repo_root,
        check=False,
    )
    if catalog.returncode != 0:
        return catalog.returncode
    print(f"validated {len(skill_dirs)} skill(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
