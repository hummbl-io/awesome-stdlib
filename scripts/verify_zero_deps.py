#!/usr/bin/env python3
"""
verify_zero_deps.py -- AST Zero-Dependency Linter for awesome-stdlib.

Parses all Python code blocks across documentation and the machine-readable
registry to mathematically guarantee zero third-party dependencies.
"""

import ast
import json
import re
import sys
from pathlib import Path


def get_stdlib_module_names() -> set[str]:
    """Returns the comprehensive set of standard library module names."""
    if hasattr(sys, "stdlib_module_names"):
        names = set(sys.stdlib_module_names)
    else:
        names = set(sys.builtin_module_names)
    
    # Common internal/platform standard modules
    names.update({"tomllib", "wsgiref", "_thread", "_winapi", "winreg", "posix", "nt", "msvcrt"})
    return names


def verify_code_snippet(code: str, context_name: str) -> list[str]:
    """Parses code and returns a list of illegal non-stdlib imports."""
    errors = []
    stdlib_names = get_stdlib_module_names()

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"{context_name}: SyntaxError: {e}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                if root_pkg not in stdlib_names:
                    errors.append(f"{context_name}: Illegal third-party import 'import {alias.name}'")
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and not node.level
            and node.module.split(".")[0] not in stdlib_names
        ):
            errors.append(f"{context_name}: Illegal third-party import 'from {node.module} import ...'")

    return errors


def extract_python_blocks_from_markdown(md_path: Path) -> list[tuple[int, str]]:
    """Extracts all fenced python code blocks from a markdown file."""
    with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    pattern = re.compile(r"```python\s*(.*?)\s*```", re.DOTALL)
    blocks = []
    for i, match in enumerate(pattern.finditer(content)):
        blocks.append((i + 1, match.group(1)))
    return blocks


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    readme_path = repo_root / "README.md"
    registry_path = repo_root / "registry.json"

    print("=" * 70)
    print("awesome-stdlib :: AST Zero-Dependency Linter")
    print("=" * 70)

    total_checked = 0
    all_errors = []

    # 1. Verify README.md code snippets
    if readme_path.exists():
        blocks = extract_python_blocks_from_markdown(readme_path)
        print(f"Found {len(blocks)} Python code blocks in README.md")
        for idx, code in blocks:
            total_checked += 1
            errs = verify_code_snippet(code, f"README.md block #{idx}")
            if errs:
                all_errors.extend(errs)

    # 2. Verify registry.json code recipes
    if registry_path.exists():
        with open(registry_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            recipes = data.get("recipes", [])
            print(f"Found {len(recipes)} recipes in registry.json")
            for recipe in recipes:
                total_checked += 1
                code = recipe.get("code", "")
                name = recipe.get("name", "unnamed")
                errs = verify_code_snippet(code, f"registry.json recipe '{name}'")
                if errs:
                    all_errors.extend(errs)

    print("-" * 70)
    if all_errors:
        print(f"FAILED: {len(all_errors)} illegal imports found:")
        for err in all_errors:
            print(f"  ❌ {err}")
        return 1

    print(f"SUCCESS: {total_checked} snippets verified. 100% pure Python standard library.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
