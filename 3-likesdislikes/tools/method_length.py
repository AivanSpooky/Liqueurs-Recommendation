"""Проверка правила код-стайла: тело любой функции/метода — не более 5 строк.

Докстринг не считается. Запуск: python tools/method_length.py <каталог> [<каталог> ...]
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import Iterator

LIMIT = 5
SKIP_DIRS = {"__pycache__", ".git", "out"}


def python_files(root: Path) -> Iterator[Path]:
    return (path for path in sorted(root.rglob("*.py")) if not SKIP_DIRS & set(path.parts))


def body_length(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    body = node.body[1:] if ast.get_docstring(node) and len(node.body) > 1 else node.body
    return body[-1].end_lineno - body[0].lineno + 1


def violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    return [f"{path}:{n.lineno} {n.name}() — {body_length(n)} строк" for n in functions if body_length(n) > LIMIT]


def check(roots: list[Path]) -> list[str]:
    return [problem for root in roots for path in python_files(root) for problem in violations(path)]


def main() -> None:
    problems = check([Path(arg) for arg in sys.argv[1:]] or [Path(".")])
    print("\n".join(problems) or f"OK: все функции не длиннее {LIMIT} строк")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
