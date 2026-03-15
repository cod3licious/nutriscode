from collections.abc import Callable
from dataclasses import dataclass


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


# JS/TS files co-exist in the same codebase, so treat them as one family.
# Passing any of these extensions will scan all four.
JS_TS_FAMILY: frozenset[str] = frozenset(["js", "jsx", "ts", "tsx"])

# Populated at runtime by register_languages()
LANGUAGE_CONFIGS: dict[str, tuple[Callable, LanguageConfig]] = {}

_MATH_OPS = frozenset(["+", "-", "*", "/", "//", "**", "%", "@", "+=", "-=", "*=", "/=", "//=", "**=", "%="])
_BITWISE_OPS = frozenset(["|", "&", "^", "~", "<<", ">>", "|=", "&=", "^=", "<<=", ">>="])
_COMPARISON_OPS = frozenset(["==", "!=", "<", ">", "<=", ">=", "is", "is not", "in", "not in"])


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
        math_operators=_MATH_OPS,
        bitwise_operators=_BITWISE_OPS,
        comparison_operators=_COMPARISON_OPS,
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
        math_operators=_MATH_OPS | frozenset(["++", "--"]),
        bitwise_operators=_BITWISE_OPS,
        comparison_operators=_COMPARISON_OPS | frozenset(["===", "!=="]),
        operator_field="operator",
    )


def _make_typescript_config() -> LanguageConfig:
    cfg = _make_javascript_config()
    return LanguageConfig(
        function_node_types=cfg.function_node_types
        | frozenset(["function_signature", "method_signature", "abstract_method_signature"]),
        function_name_field=cfg.function_name_field,
        class_node_types=cfg.class_node_types | frozenset(["abstract_class_declaration"]),
        class_name_field=cfg.class_name_field,
        statement_node_types=cfg.statement_node_types,
        conditional_node_types=cfg.conditional_node_types,
        logical_node_types=cfg.logical_node_types,
        assertion_node_types=frozenset(["call_expression"]),  # TS uses assert() calls
        exception_node_types=cfg.exception_node_types,
        call_node_types=cfg.call_node_types,
        operator_node_types=cfg.operator_node_types,
        math_operators=cfg.math_operators,
        bitwise_operators=cfg.bitwise_operators,
        comparison_operators=cfg.comparison_operators,
        operator_field=cfg.operator_field,
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
        math_operators=_MATH_OPS | frozenset(["++", "--"]),
        bitwise_operators=_BITWISE_OPS,
        comparison_operators=_COMPARISON_OPS | frozenset(["instanceof"]),
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
        math_operators=_MATH_OPS,
        bitwise_operators=_BITWISE_OPS,
        comparison_operators=_COMPARISON_OPS,
        operator_field="operator",
    )


def register_languages() -> None:
    """Lazily import language modules and populate LANGUAGE_CONFIGS."""
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
