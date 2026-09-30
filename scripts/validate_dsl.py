#!/usr/bin/env python3
"""Validate Dify Workflow DSL YAML files before delivery.

Checks structure (nodes, edges, handles, dependencies), references
(variable selectors, interpolation), and code nodes (entry function,
parameter names, return keys vs declared outputs).

Usage:
    python3 validate_dsl.py <file.yml> [more.yml ...]

Exit code 1 when any ERROR is reported.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: python3 -m pip install pyyaml") from exc

SUPPORTED_MODES = {"workflow", "advanced-chat", "chat", "completion", "agent-chat"}
TERMINAL_BY_MODE = {"workflow": "end", "advanced-chat": "answer"}
GRAPH_MODES = {"workflow", "advanced-chat"}
DEPENDENCY_TYPES = {"marketplace", "package", "github"}
WRAPPER_TYPES = {None, "custom", "custom-iteration-start", "custom-loop-start", "custom-note"}

# Official node type enum (web/app/components/workflow/types.ts).
NODE_TYPES = {
    "start", "end", "answer", "llm", "knowledge-retrieval", "question-classifier",
    "if-else", "code", "template-transform", "http-request", "variable-assigner",
    "variable-aggregator", "tool", "parameter-extractor", "iteration",
    "iteration-start", "assigner", "agent", "agent-v2", "loop", "loop-start",
    "loop-end", "human-input", "datasource", "datasource-empty", "knowledge-index",
    "trigger-schedule", "trigger-webhook", "trigger-plugin",
}

CODE_OUTPUT_TYPES = {
    "string", "number", "object", "array[string]", "array[number]", "array[object]",
}

# Structured selector fields: value must be a list whose first item is a node id or system root.
SELECTOR_KEYS = {
    "value_selector", "variable_selector", "query", "iterator_selector",
    "output_selector", "input_selector", "query_variable_selector",
}
SYSTEM_ROOTS = {"sys", "conversation", "env", "context"}

SQL_DANGEROUS_RE = re.compile(r"\b(drop|truncate|alter)\b", re.IGNORECASE)
SQL_MUTATING_RE = re.compile(r"\b(delete|update)\b", re.IGNORECASE)
SQL_TRAILING_COMMA_RE = re.compile(r"\([^;]*,\s*\)", re.IGNORECASE | re.DOTALL)
VAR_REF_RE = re.compile(r"\{\{#([^#{}]+)#\}\}")

PYTHON_MAIN_RE = re.compile(r"def\s+main\s*\(([^)]*)\)")
LITERAL_RETURN_RE = re.compile(r"return\s*\{([^{}]*)\}", re.DOTALL)
DICT_KEY_RE = re.compile(r"(?:[\"']([^\"']+)[\"']\s*:|([A-Za-z_$][\w$]*)\s*:)")


class Report:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def walk(value: Any):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def extract_tool_sql(data: dict[str, Any]) -> list[str]:
    sql_values: list[str] = []
    params = as_dict(data.get("tool_parameters"))
    for key in ("query", "sql"):
        param = as_dict(params.get(key))
        value = param.get("value")
        if isinstance(value, str):
            sql_values.append(value)
    return sql_values


def parse_literal_dict_keys(literal: str) -> list[str]:
    keys: list[str] = []
    for match in DICT_KEY_RE.finditer(literal):
        key = match.group(1) or match.group(2)
        if key and key not in keys:
            keys.append(key)
    return keys


def parse_python_params(signature: str) -> tuple[list[str], bool]:
    """Return (parameter names, has_varargs)."""
    params: list[str] = []
    has_varargs = False
    for raw in signature.split(","):
        raw = raw.strip()
        if not raw:
            continue
        if raw.startswith("*"):
            has_varargs = True
            continue
        name = raw.split(":")[0].split("=")[0].strip()
        if name:
            params.append(name)
    return params, has_varargs


def validate_code_node(report: Report, node_id: str, data: dict[str, Any]) -> None:
    title = data.get("title", node_id)
    code = data.get("code")
    language = str(data.get("code_language") or "python3").lower()
    outputs = as_dict(data.get("outputs"))
    input_names = [
        v.get("variable") for v in as_list(data.get("variables")) if isinstance(v, dict)
    ]

    if not isinstance(code, str):
        report.error(f"Code node {node_id} ({title}) missing code string.")
    if not isinstance(data.get("outputs"), dict):
        report.error(f"Code node {node_id} ({title}) missing outputs mapping.")
        outputs = {}

    unknown_types = [
        f"{key}: {as_dict(spec).get('type')!r}"
        for key, spec in outputs.items()
        if as_dict(spec).get("type") not in CODE_OUTPUT_TYPES
    ]
    if unknown_types:
        report.error(
            f"Code node {node_id} ({title}) has invalid outputs type(s) "
            f"(allowed: {sorted(CODE_OUTPUT_TYPES)}): {unknown_types}"
        )

    if not isinstance(code, str):
        return

    if language.startswith(("python", "py")):
        main_match = PYTHON_MAIN_RE.search(code)
        if not main_match:
            report.error(f"Code node {node_id} ({title}) must define def main(...).")
            return
        params, has_varargs = parse_python_params(main_match.group(1))
        check_main_signature(report, node_id, title, params, has_varargs, input_names)
        check_return_keys(report, node_id, title, code, outputs)
    elif language.startswith(("javascript", "typescript", "js", "ts")):
        if not re.search(r"\bfunction\s+main\s*\(|\bmain\s*=\s*(?:async\s*)?\(", code):
            report.error(f"Code node {node_id} ({title}) must define function main(...).")
            return
        if "..." in code:
            check_return_keys(report, node_id, title, code, outputs)
            return
        call_match = re.search(r"\bmain\s*\(([^)]*)\)\s*\{", code)
        params: list[str] = []
        if call_match:
            params = [p.strip() for p in call_match.group(1).split(",") if p.strip()]
        check_main_signature(report, node_id, title, params, False, input_names)
        check_return_keys(report, node_id, title, code, outputs)


def check_main_signature(
    report: Report,
    node_id: str,
    title: str,
    params: list[str],
    has_varargs: bool,
    input_names: list[Any],
) -> None:
    if has_varargs:
        report.warn(
            f"Code node {node_id} ({title}) uses *args/**kwargs; "
            "parameter names cannot be checked statically."
        )
        return
    declared = {name for name in input_names if isinstance(name, str)}
    actual = set(params)
    if declared == actual:
        return
    missing = sorted(declared - actual)
    extra = sorted(actual - declared)
    report.error(
        f"Code node {node_id} ({title}) main() parameters do not match input variables: "
        f"missing for inputs {missing}, unknown parameters {extra}."
    )


def check_return_keys(report: Report, node_id: str, title: str, code: str, outputs: dict[str, Any]) -> None:
    literals = LITERAL_RETURN_RE.findall(code)
    if not literals:
        report.warn(
            f"Code node {node_id} ({title}) has no literal return dict; "
            "return keys could not be checked statically — verify keys match outputs manually."
        )
        return
    output_keys = set(outputs)
    for literal in literals:
        keys = parse_literal_dict_keys(literal)
        if not keys:
            continue
        if set(keys) != output_keys:
            report.error(
                f"Code node {node_id} ({title}) return keys {sorted(set(keys))} do not "
                f"match declared outputs {sorted(output_keys)}."
            )
            return


def validate_node(report: Report, node_id: str, data: dict[str, Any]) -> None:
    node_type = data.get("type")
    title = data.get("title", node_id)

    if node_type == "llm":
        model = as_dict(data.get("model"))
        if not model.get("provider") or not model.get("name"):
            report.warn(f"LLM node {node_id} ({title}) missing model.provider or model.name.")
        if not isinstance(data.get("prompt_template"), list):
            report.error(f"LLM node {node_id} ({title}) missing prompt_template list.")

    elif node_type == "code":
        validate_code_node(report, node_id, data)

    elif node_type == "tool":
        required = ["provider_id", "provider_name", "provider_type", "tool_name", "tool_parameters"]
        for key in required:
            if data.get(key) in (None, ""):
                report.error(f"Tool node {node_id} ({title}) missing {key}.")
        if data.get("plugin_id") and not data.get("plugin_unique_identifier"):
            report.warn(f"Tool node {node_id} ({title}) has plugin_id but no plugin_unique_identifier.")
        for sql in extract_tool_sql(data):
            if SQL_TRAILING_COMMA_RE.search(sql):
                report.error(f"Tool node {node_id} ({title}) SQL may contain a trailing comma before ')'.")
            if SQL_DANGEROUS_RE.search(sql):
                report.warn(f"Tool node {node_id} ({title}) SQL contains admin/destructive keyword.")
            if SQL_MUTATING_RE.search(sql):
                report.warn(f"Tool node {node_id} ({title}) SQL mutates data; confirm this is intentional.")

    elif node_type == "if-else":
        if not isinstance(data.get("cases"), list):
            report.error(f"If-else node {node_id} ({title}) missing cases list.")

    elif node_type == "start":
        variables = as_list(data.get("variables"))
        names = [v.get("variable") for v in variables if isinstance(v, dict)]
        duplicates = [name for name, count in Counter(names).items() if name and count > 1]
        if duplicates:
            report.error(f"Start node {node_id} ({title}) has duplicate variables: {duplicates}.")

    elif node_type == "answer":
        if "answer" not in data:
            report.error(f"Answer node {node_id} ({title}) missing answer.")

    elif node_type == "end":
        if not isinstance(data.get("outputs"), list):
            report.error(f"End node {node_id} ({title}) missing outputs list.")

    elif node_type == "parameter-extractor":
        if not isinstance(data.get("parameters"), list):
            report.error(f"Parameter extractor node {node_id} ({title}) missing parameters list.")


def validate_variables(report: Report, workflow: dict[str, Any]) -> None:
    for field in ("conversation_variables", "environment_variables"):
        variables = as_list(workflow.get(field))
        names = [v.get("name") for v in variables if isinstance(v, dict)]
        duplicates = [name for name, count in Counter(names).items() if name and count > 1]
        if duplicates:
            report.error(f"{field} has duplicate names: {duplicates}.")
        for variable in variables:
            if not isinstance(variable, dict):
                report.error(f"{field} contains a non-mapping item.")
                continue
            if not variable.get("name") or not variable.get("value_type"):
                report.warn(f"{field} item is missing name or value_type: {variable!r}.")


def validate_dependencies(report: Report, document: dict[str, Any]) -> None:
    dependencies = document.get("dependencies")
    if dependencies is None:
        return
    if not isinstance(dependencies, list):
        report.error("Top-level dependencies must be a list when present.")
        return

    for index, dependency in enumerate(dependencies):
        if not isinstance(dependency, dict):
            report.error(f"Dependency #{index} is not a mapping.")
            continue
        dependency_type = dependency.get("type")
        value = as_dict(dependency.get("value"))
        if dependency_type not in DEPENDENCY_TYPES:
            report.error(f"Dependency #{index} has unsupported type: {dependency_type!r}.")
            continue
        if dependency_type == "marketplace":
            if not value.get("marketplace_plugin_unique_identifier"):
                report.error(f"Dependency #{index} marketplace value missing marketplace_plugin_unique_identifier.")
        elif dependency_type == "package":
            if not value.get("plugin_unique_identifier"):
                report.error(f"Dependency #{index} package value missing plugin_unique_identifier.")
        elif dependency_type == "github":
            required = ["repo", "version", "package", "github_plugin_unique_identifier"]
            missing = [key for key in required if not value.get(key)]
            if missing:
                report.error(f"Dependency #{index} github value missing: {missing}.")


def validate_selectors(report: Report, document: dict[str, Any], node_ids: set[str]) -> None:
    for key, value in walk(document):
        if key not in SELECTOR_KEYS or not isinstance(value, list) or not value:
            continue
        root = value[0]
        if not isinstance(root, str):
            report.error(f"Selector {key} must start with a node id or system root: {value!r}.")
            continue
        if root in SYSTEM_ROOTS or root in node_ids:
            continue
        report.error(f"Selector {key} references unknown node/root {root!r}: {value!r}.")


def validate_references(report: Report, document: dict[str, Any], node_ids: set[str]) -> None:
    roots = SYSTEM_ROOTS | node_ids
    for key, value in walk(document):
        if key == "code" or not isinstance(value, str):
            continue
        for match in VAR_REF_RE.finditer(value):
            ref = match.group(1)
            root = ref.split(".", 1)[0]
            if root not in roots:
                report.warn(f"Variable reference points to unknown node/root: {match.group(0)}.")


def validate_file(path: Path) -> Report:
    report = Report(path)
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        report.error(f"YAML parse failed: {exc}")
        return report

    if not isinstance(document, dict):
        report.error("Top-level YAML must be a mapping.")
        return report

    version = document.get("version")
    if not isinstance(version, str):
        report.error("Top-level version must be a string, for example version: \"0.6.0\".")

    if document.get("kind") != "app":
        report.warn("Top-level kind is usually 'app'.")

    app = as_dict(document.get("app"))
    mode = app.get("mode")
    if mode not in SUPPORTED_MODES:
        report.error(f"app.mode is missing or unsupported: {mode!r}.")

    workflow = as_dict(document.get("workflow"))
    graph = as_dict(workflow.get("graph"))
    nodes = as_list(graph.get("nodes"))
    edges = as_list(graph.get("edges"))

    if mode in GRAPH_MODES:
        if not nodes:
            report.error("workflow.graph.nodes is missing or empty.")
        if "edges" not in graph:
            report.error("workflow.graph.edges is missing.")
    elif not nodes and "model_config" not in document:
        report.warn(f"Mode {mode!r} has no workflow graph and no model_config.")

    node_by_id: dict[str, dict[str, Any]] = {}
    node_type_by_id: dict[str, str] = {}
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            report.error(f"Node #{index} is not a mapping.")
            continue
        node_id = node.get("id")
        if not isinstance(node_id, str):
            report.error(f"Node #{index} id must be a string.")
            continue
        if node_id in node_by_id:
            report.error(f"Duplicate node id: {node_id}.")
        node_by_id[node_id] = node
        wrapper_type = node.get("type")
        data = as_dict(node.get("data"))
        if wrapper_type == "custom-note":
            continue
        node_type = data.get("type")
        if not isinstance(node_type, str):
            report.error(f"Node {node_id} missing data.type.")
            continue
        if node_type not in NODE_TYPES:
            report.error(f"Node {node_id} ({data.get('title', node_id)}) has unknown data.type: {node_type!r}.")
            continue
        node_type_by_id[node_id] = node_type
        if wrapper_type not in WRAPPER_TYPES:
            report.warn(f"Node {node_id} wrapper type is unusual: {wrapper_type!r}.")

        validate_node(report, node_id, data)

    terminal = TERMINAL_BY_MODE.get(mode)
    if terminal and terminal not in node_type_by_id.values():
        report.warn(f"Mode {mode!r} usually needs a reachable {terminal!r} node.")

    edge_ids: set[str] = set()
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            report.error(f"Edge #{index} is not a mapping.")
            continue
        edge_id = edge.get("id")
        if isinstance(edge_id, str):
            if edge_id in edge_ids:
                report.error(f"Duplicate edge id: {edge_id}.")
            edge_ids.add(edge_id)

        source = edge.get("source")
        target = edge.get("target")
        if source not in node_by_id:
            report.error(f"Edge {edge_id or index} source does not exist: {source!r}.")
        if target not in node_by_id:
            report.error(f"Edge {edge_id or index} target does not exist: {target!r}.")

        data = as_dict(edge.get("data"))
        source_type = data.get("sourceType")
        target_type = data.get("targetType")
        if source in node_type_by_id and source_type and source_type != node_type_by_id[source]:
            report.error(
                f"Edge {edge_id or index} sourceType {source_type!r} does not match "
                f"node {source} type {node_type_by_id[source]!r}."
            )
        if target in node_type_by_id and target_type and target_type != node_type_by_id[target]:
            report.error(
                f"Edge {edge_id or index} targetType {target_type!r} does not match "
                f"node {target} type {node_type_by_id[target]!r}."
            )
        if edge.get("sourceHandle") is None:
            report.warn(f"Edge {edge_id or index} missing sourceHandle.")
        if edge.get("targetHandle") is None:
            report.warn(f"Edge {edge_id or index} missing targetHandle.")

    validate_variables(report, workflow)
    validate_dependencies(report, document)
    validate_selectors(report, document, set(node_by_id))
    validate_references(report, document, set(node_by_id))
    return report


def print_report(report: Report) -> None:
    print(f"== {report.path}")
    for error in report.errors:
        print(f"ERROR: {error}")
    for warning in report.warnings:
        print(f"WARN: {warning}")
    if not report.errors and not report.warnings:
        print("OK")
    else:
        print(f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Dify Workflow DSL YAML files.")
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()

    exit_code = 0
    for path in args.files:
        report = validate_file(path)
        print_report(report)
        if report.errors:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
