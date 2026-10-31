"""Validate this repository's package and local links; no network or resume access."""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def validate(root: Path) -> list[str]:
    errors = []
    skill = root / "skills/canada-resume"
    required = ["README.md", "README.zh-CN.md", "LICENSE", "CONTRIBUTING.md",
                "skills/canada-resume/SKILL.md", "skills/canada-resume/agents/openai.yaml"]
    for name in required:
        if not (root / name).is_file():
            errors.append(f"Missing required file: {name}")
    entry = skill / "SKILL.md"
    if entry.is_file():
        content = entry.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        if len(parts) != 3 or parts[0].strip():
            errors.append("SKILL.md needs YAML frontmatter")
        else:
            for key in ("name", "description"):
                match = re.search(rf"^{key}: (.+)$", parts[1], re.M)
                if not match:
                    errors.append(f"Missing skill {key}")
                elif key == "name" and match[1] != skill.name:
                    errors.append("Skill name must match its folder")
                elif key == "description" and len(match[1]) > 1024:
                    errors.append("Skill description exceeds 1024 characters")
        if len(content.splitlines()) >= 500:
            errors.append("Move detailed skill content into references")
    checked = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix.lower() in (".pdf", ".docx"):
            errors.append(f"Unexpected document in public package: {path.relative_to(root)}")
        if path.suffix == ".md":
            body = path.read_text(encoding="utf-8")
            targets = re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", body)
            targets += re.findall(r'src="([^"]+)"', body)
            for target in targets:
                parsed = urlsplit(target)
                if parsed.scheme or not parsed.path:
                    continue
                destination = (path.parent / unquote(parsed.path)).resolve()
                if not destination.is_relative_to(root.resolve()):
                    errors.append(f"Link leaves package in {path.relative_to(root)}: {target}")
                elif not destination.exists():
                    errors.append(f"Broken link in {path.relative_to(root)}: {target}")
                checked.append(target)
        elif path.suffix == ".svg":
            try:
                svg = ET.parse(path).getroot()
                if not svg.tag.endswith("svg"):
                    errors.append(f"Not an SVG: {path.name}")
                if svg.find("{http://www.w3.org/2000/svg}title") is None:
                    errors.append(f"Missing accessible title: {path.name}")
            except ET.ParseError as exc:
                errors.append(f"Invalid SVG {path.name}: {exc}")
    return errors


if __name__ == "__main__":
    problems = validate(ROOT)
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    print("PASS: required files, skill metadata, relative links, SVG structure, and document exclusions.")
    print("Not tested: external links, full YAML schema, AI behavior, document export, or ATS compatibility.")
