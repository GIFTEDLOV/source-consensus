#!/usr/bin/env python3
"""Build the Bradbury deployable source and prove AST equivalence.

Only comments and Python docstrings are removed. Runtime strings, decorators, prompts, and code
are preserved. The canonical audited source is never modified.
"""
from __future__ import annotations

import ast
import io
import pathlib
import tokenize


def docstring_spans(tree: ast.AST) -> set[tuple[int, int, int, int]]:
    spans = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
            value = body[0].value
            spans.add((value.lineno, value.col_offset, value.end_lineno, value.end_col_offset))
    return spans


class StripDocstrings(ast.NodeTransformer):
    def _strip(self, node):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) and isinstance(body[0].value.value, str):
            node.body = body[1:]
        return self.generic_visit(node)

    visit_Module = _strip
    visit_FunctionDef = _strip
    visit_AsyncFunctionDef = _strip
    visit_ClassDef = _strip


def build(source: pathlib.Path, target: pathlib.Path) -> None:
    text = source.read_text(encoding="utf-8")
    tree = ast.parse(text)
    spans = docstring_spans(tree)
    runner_header = next((line for line in text.splitlines() if line.startswith("# { \"Depends\": ")), None)
    tokens = []
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        inside_doc = any((sl, sc) <= token.start and token.end <= (el, ec) for sl, sc, el, ec in spans)
        if token.type == tokenize.COMMENT or inside_doc:
            continue
        tokens.append(token)
    deployable = tokenize.untokenize(tokens)
    if runner_header is None:
        raise SystemExit("missing GenVM runner header in canonical source")
    deployable = runner_header + "\n" + deployable.lstrip("\n")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(deployable, encoding="utf-8", newline="\n")
    canonical = ast.parse(text)
    built = ast.parse(deployable)
    canonical = StripDocstrings().visit(canonical)
    built = StripDocstrings().visit(built)
    if ast.dump(canonical, include_attributes=False) != ast.dump(built, include_attributes=False):
        raise SystemExit("AST equivalence failed")
    print(f"AST equivalent: {source} -> {target}")
    print(f"canonical_bytes={len(text.encode('utf-8'))} deployable_bytes={len(deployable.encode('utf-8'))}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("target", type=pathlib.Path)
    args = parser.parse_args()
    build(args.source, args.target)
