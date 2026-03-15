import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from tree_sitter import Language, Node, Parser

# ---------------------------------------------------------------------------
# Coefficients (all configurable)
# ---------------------------------------------------------------------------

COEF_MATH = 1.0
COEF_BITWISE = 0.8
COEF_CONDITIONAL = 0.4
COEF_LOGICAL = 0.6
COEF_COMPARISON = 0.5
COEF_CALL = 0.3  # single unified call coefficient (no internal/external split)
COEF_ASSERT = 0.2
COEF_EXCEPTION = 0.1


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
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Language configuration
# ---------------------------------------------------------------------------


@dataclass
class LanguageConfig:
    """Maps tree-sitter node types to metric categories for one language."""

    # Node types that define a function/method (we score each separately)
    function_node_types: frozenset[str]

    # Node type used to get the function name (field or child type)
    function_name_field: str  # field name on the function node, e.g. "name"

    # Node types for classes (to build dotted paths)
    class_node_types: frozenset[str]
    class_name_field: str

    # Node types counted as statements (denominator)
    statement_node_types: frozenset[str]

    # Node types that are unconditionally one category
    conditional_node_types: frozenset[str]
    logical_node_types: frozenset[str]
    assertion_node_types: frozenset[str]
    exception_node_types: frozenset[str]
    call_node_types: frozenset[str]

    # Binary/unary operator nodes where we must inspect the operator text
    # to distinguish math vs bitwise vs comparison
    operator_node_types: frozenset[str]

    math_operators: frozenset[str]
    bitwise_operators: frozenset[str]
    comparison_operators: frozenset[str]

    # Field name on operator nodes that holds the operator token (None = first unnamed child)
    operator_field: str | None = "operator"


MATH_OPS = frozenset(["+", "-", "*", "/", "//", "**", "%", "@", "+=", "-=", "*=", "/=", "//=", "**=", "%="])
BITWISE_OPS = frozenset(["|", "&", "^", "~", "<<", ">>", "|=", "&=", "^=", "<<=", ">>="])
COMPARISON_OPS = frozenset(["==", "!=", "<", ">", "<=", ">=", "is", "is not", "in", "not in"])


def _make_python_config() -> LanguageConfig:
    return LanguageConfig(
        function_node_types=frozenset(["function_definition", "lambda"]),
        function_name_field="name",
        class_node_types=frozenset(["class_definition"]),
        class_name_field="name",
        statement_node_types=frozenset(
            [
                "expression_statement",
                "assignment",
                "augmented_assignment",
                "annotated_assignment",
                "return_statement",
                "delete_statement",
                "pass_statement",
                "break_statement",
                "continue_statement",
                "raise_statement",
                "yield",
                "global_statement",
                "nonlocal_statement",
                "import_statement",
                "import_from_statement",
                "if_statement",
                "for_statement",
                "while_statement",
                "try_statement",
                "with_statement",
                "match_statement",
            ]
        ),
        conditional_node_types=frozenset(
            [
                "if_statement",
                "elif_clause",
                "conditional_expression",
                "for_statement",
                "while_statement",
                "match_statement",
                "case_clause",
            ]
        ),
        logical_node_types=frozenset(["boolean_operator", "not_operator"]),
        assertion_node_types=frozenset(["assert_statement"]),
        exception_node_types=frozenset(["except_clause", "finally_clause"]),
        call_node_types=frozenset(["call"]),
        operator_node_types=frozenset(["binary_operator", "unary_operator", "augmented_assignment"]),
        math_operators=MATH_OPS,
        bitwise_operators=BITWISE_OPS,
        comparison_operators=COMPARISON_OPS,
        operator_field="operator",
    )


def _make_javascript_config() -> LanguageConfig:
    return LanguageConfig(
        function_node_types=frozenset(
            [
                "function_declaration",
                "function",
                "method_definition",
                "arrow_function",
                "generator_function",
                "generator_function_declaration",
            ]
        ),
        function_name_field="name",
        class_node_types=frozenset(["class_declaration", "class"]),
        class_name_field="name",
        statement_node_types=frozenset(
            [
                "expression_statement",
                "variable_declaration",
                "lexical_declaration",
                "return_statement",
                "throw_statement",
                "break_statement",
                "continue_statement",
                "if_statement",
                "for_statement",
                "for_in_statement",
                "while_statement",
                "do_statement",
                "try_statement",
                "switch_statement",
                "import_statement",
                "export_statement",
            ]
        ),
        conditional_node_types=frozenset(
            [
                "if_statement",
                "else_clause",
                "ternary_expression",
                "for_statement",
                "for_in_statement",
                "while_statement",
                "do_statement",
                "switch_case",
                "switch_default",
            ]
        ),
        logical_node_types=frozenset(["binary_expression"]),  # handled via operator text below
        assertion_node_types=frozenset(),
        exception_node_types=frozenset(["catch_clause", "finally_clause"]),
        call_node_types=frozenset(["call_expression", "new_expression"]),
        operator_node_types=frozenset(["binary_expression", "unary_expression", "assignment_expression"]),
        math_operators=MATH_OPS | frozenset(["++", "--"]),
        bitwise_operators=BITWISE_OPS,
        comparison_operators=COMPARISON_OPS | frozenset(["===", "!=="]),
        operator_field="operator",
    )


def _make_typescript_config() -> LanguageConfig:
    cfg = _make_javascript_config()
    return LanguageConfig(
        **{
            **asdict(cfg),
            "function_node_types": cfg.function_node_types
            | frozenset(
                [
                    "function_signature",
                    "method_signature",
                    "abstract_method_signature",
                ]
            ),
            "class_node_types": cfg.class_node_types | frozenset(["abstract_class_declaration"]),
            "assertion_node_types": frozenset(["call_expression"]),  # TS uses assert() calls
        }
    )


def _make_java_config() -> LanguageConfig:
    return LanguageConfig(
        function_node_types=frozenset(
            [
                "method_declaration",
                "constructor_declaration",
                "lambda_expression",
            ]
        ),
        function_name_field="name",
        class_node_types=frozenset(
            [
                "class_declaration",
                "interface_declaration",
                "enum_declaration",
                "record_declaration",
            ]
        ),
        class_name_field="name",
        statement_node_types=frozenset(
            [
                "expression_statement",
                "local_variable_declaration",
                "return_statement",
                "throw_statement",
                "break_statement",
                "continue_statement",
                "if_statement",
                "for_statement",
                "enhanced_for_statement",
                "while_statement",
                "do_statement",
                "try_statement",
                "switch_expression",
                "assert_statement",
            ]
        ),
        conditional_node_types=frozenset(
            [
                "if_statement",
                "else",
                "ternary_expression",
                "for_statement",
                "enhanced_for_statement",
                "while_statement",
                "do_statement",
                "switch_expression",
                "switch_label",
            ]
        ),
        logical_node_types=frozenset(),  # handled via operator text
        assertion_node_types=frozenset(["assert_statement"]),
        exception_node_types=frozenset(["catch_clause", "finally_clause"]),
        call_node_types=frozenset(["method_invocation", "object_creation_expression"]),
        operator_node_types=frozenset(["binary_expression", "unary_expression", "assignment_expression", "update_expression"]),
        math_operators=MATH_OPS | frozenset(["++", "--"]),
        bitwise_operators=BITWISE_OPS,
        comparison_operators=COMPARISON_OPS | frozenset(["instanceof"]),
        operator_field="operator",
    )


def _make_go_config() -> LanguageConfig:
    return LanguageConfig(
        function_node_types=frozenset(["function_declaration", "method_declaration", "func_literal"]),
        function_name_field="name",
        class_node_types=frozenset(["type_declaration"]),  # Go has no classes but structs
        class_name_field="name",
        statement_node_types=frozenset(
            [
                "expression_statement",
                "assignment_statement",
                "short_var_declaration",
                "var_declaration",
                "return_statement",
                "go_statement",
                "defer_statement",
                "send_statement",
                "inc_statement",
                "dec_statement",
                "if_statement",
                "for_statement",
                "range_clause",
                "type_switch_statement",
                "select_statement",
                "break_statement",
                "continue_statement",
            ]
        ),
        conditional_node_types=frozenset(
            [
                "if_statement",
                "else",
                "for_statement",
                "type_switch_statement",
                "expression_switch_statement",
                "default_case",
                "expression_case",
                "select_statement",
                "communication_case",
            ]
        ),
        logical_node_types=frozenset(),  # handled via operator text
        assertion_node_types=frozenset(),
        exception_node_types=frozenset(),  # Go has no exceptions
        call_node_types=frozenset(["call_expression"]),
        operator_node_types=frozenset(["binary_expression", "unary_expression"]),
        math_operators=MATH_OPS,
        bitwise_operators=BITWISE_OPS,
        comparison_operators=COMPARISON_OPS,
        operator_field="operator",
    )


LANGUAGE_CONFIGS: dict[str, tuple[Callable, LanguageConfig]] = {}


def _register_languages() -> None:
    """Lazily import language modules and register configs."""
    entries = [
        ("py", "tree_sitter_python", _make_python_config),
        ("js", "tree_sitter_javascript", _make_javascript_config),
        ("ts", "tree_sitter_typescript", _make_typescript_config),
        ("tsx", "tree_sitter_typescript", _make_typescript_config),
        ("jsx", "tree_sitter_javascript", _make_javascript_config),
        ("java", "tree_sitter_java", _make_java_config),
        ("go", "tree_sitter_go", _make_go_config),
    ]
    for ext, module_name, config_factory in entries:
        try:
            mod = __import__(module_name)
            # TypeScript exposes language_typescript / language_tsx
            if module_name == "tree_sitter_typescript":
                lang_fn = mod.language_tsx if ext in ("tsx",) else mod.language_typescript
            else:
                lang_fn = mod.language
            LANGUAGE_CONFIGS[ext] = (lang_fn, config_factory())
        except ImportError:
            pass  # silently skip unavailable languages


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


def _score(c: _Counter) -> float:
    numerator = (
        COEF_MATH * c.math_ops
        + COEF_BITWISE * c.bitwise_ops
        + COEF_CONDITIONAL * c.conditionals
        + COEF_LOGICAL * c.logical_ops
        + COEF_COMPARISON * c.comparisons
        + COEF_CALL * max(0, c.calls - 1)
        + COEF_ASSERT * c.assertions
        + COEF_EXCEPTION * c.exception_handlers
    )
    return round(numerator / max(c.statement_count, 1), 4)


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
                    score=_score(counter),
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


def analyze_codebase(root: Path, extension: str) -> list[FunctionMetrics]:
    ext = extension.lstrip(".")
    if ext not in LANGUAGE_CONFIGS:
        available = ", ".join(sorted(LANGUAGE_CONFIGS))
        raise ValueError(f"Unsupported extension '{ext}'. Available: {available}")

    lang_fn, cfg = LANGUAGE_CONFIGS[ext]
    language = Language(lang_fn())
    parser = Parser(language)

    all_metrics: list[FunctionMetrics] = []
    for file in sorted(root.rglob(f"*.{ext}")):
        all_metrics.extend(analyse_file(file, root, cfg, parser))

    all_metrics.sort(key=lambda m: m.score)
    return all_metrics


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    _register_languages()

    ap = argparse.ArgumentParser(description="Score functions by computational density.")
    ap.add_argument("path", help="Root directory of the codebase")
    ap.add_argument("extension", help="File extension to analyse (e.g. py, ts, java)")
    ap.add_argument("--output", "-o", help="Write JSON output to this file (default: stdout)")
    ap.add_argument(
        "--min-statements", type=int, default=0, help="Exclude functions with fewer statements than this (default: 0)"
    )
    args = ap.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    metrics = analyze_codebase(root, args.extension)
    metrics = [m for m in metrics if m.statement_count >= args.min_statements]

    output = json.dumps([m.to_dict() for m in metrics], indent=2)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Wrote {len(metrics)} function scores to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
