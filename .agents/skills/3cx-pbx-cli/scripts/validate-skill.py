#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Final, Iterable


SKILL_NAME: Final = "3cx-pbx-cli"
MAX_SKILL_LINES: Final = 500
ALLOWED_FRONTMATTER_KEYS: Final = frozenset(
    {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
)
REQUIRED_REFERENCES: Final = (
    "references/configuration-api.md",
    "references/call-control-api.md",
    "references/live-safety.md",
)
NAME_PATTERN: Final = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FIRST_OR_SECOND_PERSON_PATTERN: Final = re.compile(
    r"\b(?:I|me|my|mine|we|us|our|ours|you|your|yours)\b", re.IGNORECASE
)
NEGATIVE_TRIGGER_PATTERN: Final = re.compile(
    r"\b(?:do not use|don't use|not for|avoid|excludes?)\b", re.IGNORECASE
)
MARKDOWN_LINK_PATTERN: Final = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
CREDENTIAL_PATTERNS: Final = (
    ("private key", re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("provider token", re.compile(r"\b(?:sk|ghp|github_pat|AKIA)[-_A-Za-z0-9]{16,}\b")),
)
ASSIGNED_CREDENTIAL_PATTERN: Final = re.compile(
    r"(?i)(?:--?(?:api[-_]?key|client[-_]?secret|password|token)|"
    r"(?:api[-_]?key|client[-_]?secret|password|access[-_]?token)\s*[:=])"
    r"\s*[=]?\s*['\"]?([^\s'\"`]+)"
)
SAFE_CREDENTIAL_VALUE_PATTERN: Final = re.compile(
    r"(?i)^(?:<[^>]+>|\[[^]]+\]|\$\{?[A-Z_][A-Z0-9_]*\}?|"
    r"YOUR[_-][A-Z0-9_-]+|REDACTED|PLACEHOLDER|EXAMPLE|xxx+|\.\.\.)$"
)


def parse_frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, ["SKILL.md must start with YAML frontmatter delimiter '---'"]

    try:
        closing_index = next(
            index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration:
        return {}, ["SKILL.md frontmatter is missing its closing '---' delimiter"]

    values: dict[str, str] = {}
    frontmatter_lines = lines[1:closing_index]
    index = 0
    while index < len(frontmatter_lines):
        line = frontmatter_lines[index]
        index += 1
        if not line.strip() or line.lstrip().startswith("#") or line.startswith((" ", "\t")):
            continue
        if ":" not in line:
            errors.append(f"invalid frontmatter line: {line!r}")
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if key in values:
            errors.append(f"duplicate frontmatter field: {key}")
            continue
        if key not in ALLOWED_FRONTMATTER_KEYS:
            errors.append(f"unsupported frontmatter field: {key}")

        value = raw_value.strip().strip("'\"")
        if value in {">", "|", ">-", "|-", ">+", "|+"}:
            block: list[str] = []
            while index < len(frontmatter_lines):
                candidate = frontmatter_lines[index]
                if candidate and not candidate.startswith((" ", "\t")):
                    break
                block.append(candidate.strip())
                index += 1
            value = " ".join(part for part in block if part)
        values[key] = value

    return values, errors


def validate_metadata(skill_file: Path, text: str) -> list[str]:
    metadata, errors = parse_frontmatter(text)
    name = metadata.get("name", "")
    description = metadata.get("description", "")

    if name != SKILL_NAME:
        errors.append(f"frontmatter name must be {SKILL_NAME!r}, found {name!r}")
    if not NAME_PATTERN.fullmatch(name) or not 1 <= len(name) <= 64:
        errors.append("frontmatter name must be 1-64 lowercase letters, digits, or single hyphens")
    if not description:
        errors.append("frontmatter description is required")
    elif len(description) > 1024:
        errors.append("frontmatter description must not exceed 1024 characters")
    elif FIRST_OR_SECOND_PERSON_PATTERN.search(description):
        errors.append("frontmatter description must be written in the third person")
    if description and not NEGATIVE_TRIGGER_PATTERN.search(description):
        errors.append("frontmatter description must include a negative trigger")
    if len(text.splitlines()) > MAX_SKILL_LINES:
        errors.append(
            f"{skill_file.name} exceeds {MAX_SKILL_LINES} lines "
            f"({len(text.splitlines())} found)"
        )
    return errors


def markdown_files(skill_root: Path) -> tuple[Path, ...]:
    return (skill_root / "SKILL.md",) + tuple(
        skill_root / relative_path for relative_path in REQUIRED_REFERENCES
    )


def validate_links(skill_root: Path, files: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    resolved_root = skill_root.resolve()
    skill_file = skill_root / "SKILL.md"
    if skill_file.is_file():
        skill_text = skill_file.read_text(encoding="utf-8")
        for required_reference in REQUIRED_REFERENCES:
            if required_reference not in skill_text:
                errors.append(f"SKILL.md must link to {required_reference}")
    for source in files:
        if not source.is_file():
            continue
        text = source.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK_PATTERN.finditer(text):
            raw_target = match.group(1).strip().split()[0].strip("<>")
            target = raw_target.split("#", 1)[0]
            if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE):
                continue
            if target.startswith(("/", "~")) or re.match(r"^[A-Za-z]:[/\\]", target):
                errors.append(f"{source.relative_to(skill_root)} uses absolute link {raw_target!r}")
                continue
            resolved_target = (source.parent / target).resolve()
            try:
                resolved_target.relative_to(resolved_root)
            except ValueError:
                errors.append(f"{source.relative_to(skill_root)} link escapes skill root: {raw_target!r}")
                continue
            if not resolved_target.exists():
                errors.append(f"{source.relative_to(skill_root)} has missing link target {raw_target!r}")
    return errors


def validate_secrets(skill_root: Path, files: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    for source in files:
        if not source.is_file():
            continue
        text = source.read_text(encoding="utf-8")
        relative_source = source.relative_to(skill_root)
        for label, pattern in CREDENTIAL_PATTERNS:
            if pattern.search(text):
                errors.append(f"{relative_source} contains a prohibited {label}")
        for match in ASSIGNED_CREDENTIAL_PATTERN.finditer(text):
            value = match.group(1).rstrip(",;)")
            if not SAFE_CREDENTIAL_VALUE_PATTERN.fullmatch(value):
                line_number = text.count("\n", 0, match.start()) + 1
                errors.append(
                    f"{relative_source}:{line_number} contains a literal secret-like value"
                )
    return errors


def parser_subcommands(parser_file: Path) -> tuple[str, ...]:
    tree = ast.parse(parser_file.read_text(encoding="utf-8"), filename=str(parser_file))
    commands: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "add_parser" or not node.args:
            continue
        argument = node.args[0]
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            commands.append((node.lineno, argument.value))
    return tuple(command for _, command in sorted(commands))


def find_repo_root(script_file: Path, working_directory: Path) -> Path | None:
    candidates = (script_file.parents[4], working_directory, *working_directory.parents)
    for candidate in candidates:
        if (candidate / "threecx/config_parser.py").is_file() and (
            candidate / "threecx/call_parser.py"
        ).is_file():
            return candidate
    return None


def validate_command_coverage(repo_root: Path, files: Iterable[Path]) -> list[str]:
    combined_text = "\n".join(
        source.read_text(encoding="utf-8") for source in files if source.is_file()
    )
    errors: list[str] = []
    parser_contracts = (
        ("3cx-config", repo_root / "threecx/config_parser.py"),
        ("3cx-call", repo_root / "threecx/call_parser.py"),
    )
    for cli_name, parser_file in parser_contracts:
        if not parser_file.is_file():
            errors.append(f"missing CLI parser source: {parser_file.relative_to(repo_root)}")
            continue
        missing = [
            command
            for command in parser_subcommands(parser_file)
            if f"`{command}`" not in combined_text
        ]
        if missing:
            errors.append(f"{cli_name} subcommands missing from skill artifacts: {', '.join(missing)}")
    return errors


def validate() -> tuple[list[str], list[str]]:
    script_file = Path(__file__).resolve()
    skill_root = script_file.parent.parent
    repo_root = find_repo_root(script_file, Path.cwd().resolve())
    files = markdown_files(skill_root)
    errors: list[str] = []
    notices: list[str] = []

    for required_file in files:
        if not required_file.is_file():
            errors.append(f"missing required file: {required_file.relative_to(skill_root)}")
    skill_file = skill_root / "SKILL.md"
    if skill_file.is_file():
        errors.extend(validate_metadata(skill_file, skill_file.read_text(encoding="utf-8")))
    errors.extend(validate_links(skill_root, files))
    errors.extend(validate_secrets(skill_root, files))
    if repo_root is None:
        notices.append(
            "dynamic command-source verification skipped: "
            "threecx/config_parser.py and threecx/call_parser.py were not found"
        )
    else:
        errors.extend(validate_command_coverage(repo_root, files))
    return errors, notices


def main() -> int:
    try:
        errors, notices = validate()
    except (OSError, UnicodeError, SyntaxError) as error:
        print(f"ERROR: validator could not inspect artifacts: {error}", file=sys.stderr)
        return 2

    for notice in notices:
        print(f"NOTICE: {notice}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"3cx-pbx-cli skill validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    print("3cx-pbx-cli skill validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
