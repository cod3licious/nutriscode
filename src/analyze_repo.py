import argparse
import json
import sys
from dataclasses import dataclass, fields
from pathlib import Path

from tree_sitter import Language, Node, Parser

from languages import JS_TS_FAMILY, LANGUAGE_CONFIGS, LanguageConfig, register_languages

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class FunctionMetrics:
    name: str  # dotted path: package.module.Class.method
    statement_count: int
    math_ops: int
    bitwise_ops: int
    conditionals: int
    assertions: int
    logical_ops: int
    comparisons: int
    calls: int
    exception_handlers: int

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name != "name"}


# ---------------------------------------------------------------------------
# Metric extraction
# ---------------------------------------------------------------------------


@dataclass
class _Counter:
    statement_count: int = 0
    math_ops: int = 0
    bitwise_ops: int = 0
    conditionals: int = 0
    assertions: int = 0
    logical_ops: int = 0
    comparisons: int = 0
    calls: int = 0
    exception_handlers: int = 0


def _get_operator_text(node: Node, cfg: LanguageConfig) -> str | None:
    """Extract the operator token text from a binary/unary operator node."""
    if cfg.operator_field:
        op_node = node.child_by_field_name(cfg.operator_field)
        if op_node:
            return op_node.text.decode("utf-8") if op_node.text else None
    # Fallback: first unnamed child
    for child in node.children:
        if not child.is_named:
            return child.text.decode("utf-8") if child.text else None
    return None


def _count_node(node: Node, cfg: LanguageConfig, counter: _Counter, is_root_function: bool = False) -> None:
    """
    Recursively walk `node`, accumulating metrics into `counter`.
    Stops descending into nested function definitions (they are scored separately),
    except for lambdas which are counted inline in their enclosing function.
    """
    ntype = node.type

    # Skip type annotation subtrees — operators there are type syntax, not computation
    if ntype in cfg.type_annotation_node_types:
        return

    # Stop at nested non-lambda functions — they get their own score entry
    if not is_root_function and ntype in cfg.function_node_types:
        is_lambda = ntype == "lambda" or "lambda" in ntype or "arrow" in ntype
        if not is_lambda:
            return

    # Statements
    if ntype in cfg.statement_node_types:
        counter.statement_count += 1

    # Conditionals
    if ntype in cfg.conditional_node_types:
        counter.conditionals += 1

    # Logical operators
    if ntype in cfg.logical_node_types:
        # JS/Java: logical ops are binary_expression with &&, ||, ! operators
        # Python: boolean_operator / not_operator are distinct node types
        if ntype in cfg.operator_node_types:
            op = _get_operator_text(node, cfg)
            if op in ("&&", "||", "!", "and", "or", "not"):
                counter.logical_ops += 1
                # Don't double-count via operator_node_types below
                for child in node.children:
                    _count_node(child, cfg, counter)
                return
        else:
            counter.logical_ops += 1

    # Assertions
    if ntype in cfg.assertion_node_types:
        counter.assertions += 1

    # Exception handlers
    if ntype in cfg.exception_node_types:
        counter.exception_handlers += 1

    # Calls
    if ntype in cfg.call_node_types:
        counter.calls += 1

    # Operator nodes: classify by operator text
    if ntype in cfg.operator_node_types:
        op = _get_operator_text(node, cfg)
        if op is not None:
            if op in cfg.math_operators:
                counter.math_ops += 1
            elif op in cfg.bitwise_operators:
                counter.bitwise_ops += 1
            elif op in cfg.comparison_operators:
                counter.comparisons += 1
            elif op in ("&&", "||", "!", "and", "or", "not"):
                counter.logical_ops += 1

    for child in node.children:
        _count_node(child, cfg, counter)


# ---------------------------------------------------------------------------
# Path construction
# ---------------------------------------------------------------------------


def _build_name(root: Path, file: Path, class_name: str | None, func_name: str) -> str:
    """
    Build dotted path: package.module.Class.method
    Strips the file extension and collapses uninformative path segments
    (single-char dirs, __init__, index, mod, etc.).
    """
    rel = file.relative_to(root)
    parts = list(rel.with_suffix("").parts)

    # Remove segments that add no disambiguation value
    uninformative = {"__init__", "index", "mod", "lib", "src", "main"}
    filtered = [p for p in parts if p not in uninformative and len(p) > 1]

    if not filtered:
        filtered = parts[-1:]  # always keep at least the filename

    if class_name:
        filtered.append(class_name)
    filtered.append(func_name)

    return ".".join(filtered)


# ---------------------------------------------------------------------------
# AST traversal for function discovery
# ---------------------------------------------------------------------------


def _extract_functions(
    node: Node,
    cfg: LanguageConfig,
    root: Path,
    file: Path,
    class_stack: list[str],
) -> list[FunctionMetrics]:
    results: list[FunctionMetrics] = []
    ntype = node.type

    # Track class context
    if ntype in cfg.class_node_types:
        name_node = node.child_by_field_name(cfg.class_name_field)
        class_name = name_node.text.decode("utf-8") if name_node and name_node.text else "?"
        class_stack = [*class_stack, class_name]

    # Found a function — score it
    if ntype in cfg.function_node_types:
        is_lambda = "lambda" in ntype or "arrow" in ntype
        if not is_lambda:
            name_node = node.child_by_field_name(cfg.function_name_field)
            func_name = name_node.text.decode("utf-8") if name_node and name_node.text else "<anonymous>"
            class_name = class_stack[-1] if class_stack else None

            counter = _Counter()
            _count_node(node, cfg, counter, is_root_function=True)

            dotted = _build_name(root, file, class_name, func_name)
            results.append(
                FunctionMetrics(
                    name=dotted,
                    statement_count=counter.statement_count,
                    math_ops=counter.math_ops,
                    bitwise_ops=counter.bitwise_ops,
                    conditionals=counter.conditionals,
                    assertions=counter.assertions,
                    logical_ops=counter.logical_ops,
                    comparisons=counter.comparisons,
                    calls=counter.calls,
                    exception_handlers=counter.exception_handlers,
                )
            )
            # Still descend to find nested named functions, but don't re-enter this one
            for child in node.children:
                results.extend(_extract_functions(child, cfg, root, file, class_stack))
            return results

    for child in node.children:
        results.extend(_extract_functions(child, cfg, root, file, class_stack))

    return results


# ---------------------------------------------------------------------------
# File and directory processing
# ---------------------------------------------------------------------------


def analyse_file(path: Path, root: Path, cfg: LanguageConfig, parser: Parser) -> list[FunctionMetrics]:
    try:
        source = path.read_bytes()
    except OSError:
        return []

    tree = parser.parse(source)
    return _extract_functions(tree.root_node, cfg, root, path, [])


def analyze_codebase(root: Path, extension: str, min_statements: int = 0) -> dict[str, dict]:
    if not LANGUAGE_CONFIGS:
        register_languages()
    ext = extension.lstrip(".")
    if ext not in LANGUAGE_CONFIGS:
        available = ", ".join(sorted(LANGUAGE_CONFIGS))
        raise ValueError(f"Unsupported extension '{ext}'. Available: {available}")

    # JS/TS files coexist in the same codebase — always scan the full family together.
    extensions = JS_TS_FAMILY if ext in JS_TS_FAMILY else [ext]

    all_metrics: list[FunctionMetrics] = []
    for e in extensions:
        if e not in LANGUAGE_CONFIGS:
            continue
        lang_fn, cfg = LANGUAGE_CONFIGS[e]
        parser = Parser(Language(lang_fn()))
        for file in sorted(root.rglob(f"*.{e}")):
            all_metrics.extend(analyse_file(file, root, cfg, parser))

    filtered = [m for m in all_metrics if m.statement_count >= min_statements]
    return {m.name: m.to_dict() for m in sorted(filtered, key=lambda m: m.name)}


def _summarize(functions: dict[str, dict]) -> dict:
    """Aggregate function metrics into a repository-level summary."""
    total: dict[str, int] = {
        "function_count": len(functions),
        "statement_count": 0,
        "math_ops": 0,
        "bitwise_ops": 0,
        "conditionals": 0,
        "assertions": 0,
        "logical_ops": 0,
        "comparisons": 0,
        "calls": 0,
        "exception_handlers": 0,
    }
    for metrics in functions.values():
        for key in total:
            if key != "function_count":
                total[key] += metrics.get(key, 0)
    return total


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(description="Score functions by computational density.")
    ap.add_argument("path", help="Root directory of the codebase")
    ap.add_argument("extension", help="File extension to analyse (e.g. py, ts, java)")
    ap.add_argument(
        "--min-statements", type=int, default=0, help="Exclude functions with fewer statements than this (default: 0)"
    )
    args = ap.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    functions = analyze_codebase(root, args.extension, args.min_statements)

    # Save per-repo results
    results_dir = Path(__file__).parent.parent / "results"
    results_dir.mkdir(exist_ok=True)

    repo_name = root.name
    repo_file = results_dir / f"{repo_name}.json"
    repo_file.write_text(json.dumps(functions, indent=2))
    print(f"Wrote {len(functions)} functions to {repo_file}")

    # Update _all.json with summary for this repo
    all_file = results_dir / "_all.json"
    all_data: dict = json.loads(all_file.read_text()) if all_file.exists() else {}
    all_data[repo_name] = _summarize(functions)
    all_file.write_text(json.dumps(all_data, indent=2))
    print(f"Updated {all_file}")

    # Update _index.json so the frontend can discover available files
    index = sorted(f.name for f in results_dir.glob("*.json") if not f.name.startswith("_"))
    (results_dir / "_index.json").write_text(json.dumps(["_all.json", *index], indent=2))


if __name__ == "__main__":
    main()
