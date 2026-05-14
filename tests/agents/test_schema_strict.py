"""Verify that .agents/schemas/implementation_result.json satisfies OpenAI strict
structured-output requirements:
  - every object schema has additionalProperties: false
  - every declared property appears in required
  - semantically optional fields use nullable types
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

SCHEMA_PATH = Path(".agents/schemas/implementation_result.json")


def _collect_object_schemas(node, path="root"):
    """Recursively yield (path, schema_dict) for every object-type schema node."""
    if not isinstance(node, dict):
        return
    if node.get("type") == "object" or (
        isinstance(node.get("type"), list) and "object" in node["type"]
    ):
        yield path, node
    for key, child in node.get("properties", {}).items():
        yield from _collect_object_schemas(child, f"{path}.properties.{key}")
    items = node.get("items")
    if isinstance(items, dict):
        yield from _collect_object_schemas(items, f"{path}.items")
    for combinator in ("anyOf", "oneOf", "allOf"):
        for i, child in enumerate(node.get(combinator, [])):
            yield from _collect_object_schemas(child, f"{path}.{combinator}[{i}]")


@pytest.fixture(scope="module")
def schema():
    assert SCHEMA_PATH.exists(), f"Schema file not found: {SCHEMA_PATH}"
    return json.loads(SCHEMA_PATH.read_text())


def test_schema_loads(schema):
    assert isinstance(schema, dict)
    assert schema.get("type") == "object"


def test_all_object_schemas_have_additionalProperties_false(schema):
    """Every object schema — including nested array item schemas — must forbid
    additional properties so OpenAI strict structured output accepts the schema."""
    violations = []
    for path, obj_schema in _collect_object_schemas(schema):
        if obj_schema.get("additionalProperties") is not False:
            violations.append(
                f"{path}: additionalProperties="
                f"{obj_schema.get('additionalProperties', '<missing>')!r}"
            )
    assert not violations, (
        "Object schemas missing 'additionalProperties: false':\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_all_required_lists_complete(schema):
    """Every declared property in every object schema must appear in required.
    OpenAI strict structured output rejects schemas where properties are declared
    but not listed in required."""
    violations = []
    for path, obj_schema in _collect_object_schemas(schema):
        props = set(obj_schema.get("properties", {}).keys())
        required = set(obj_schema.get("required", []))
        missing = props - required
        if missing:
            violations.append(
                f"{path}: properties not in required: {sorted(missing)}"
            )
    assert not violations, (
        "Object schemas with properties missing from required "
        "(add them; use nullable types for optional fields):\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_no_open_metadata_field(schema):
    """metadata must not exist as an open-ended object in the schema."""
    props = schema.get("properties", {})
    assert "metadata" not in props, (
        "Schema contains a 'metadata' field — open-ended metadata is incompatible "
        "with OpenAI strict structured output. Remove it or convert to a closed schema."
    )


def test_required_fields_complete(schema):
    """All declared top-level properties must be in required."""
    declared = set(schema.get("properties", {}).keys())
    required = set(schema.get("required", []))
    assert declared == required, (
        f"Top-level required mismatch. "
        f"Declared but not required: {sorted(declared - required)}. "
        f"Required but not declared: {sorted(required - declared)}."
    )


def test_status_enum_values(schema):
    status = schema["properties"]["status"]
    assert set(status["enum"]) == {"success", "partial", "failed", "skipped"}


def test_optional_fields_are_nullable(schema):
    """Semantically optional top-level fields must allow null so the model can
    omit a value by returning null without violating the required constraint."""
    optional_fields = [
        "files_changed", "validation_results", "issues",
        "proposed_followup_tasks", "completed_at",
    ]
    for name in optional_fields:
        field = schema["properties"][name]
        t = field.get("type", [])
        assert "null" in t, (
            f"Field '{name}' is optional but does not allow null. "
            f"Set type to [\"{t}\", \"null\"] or [\"null\", \"{t}\"]."
        )


def test_validation_results_items_strict(schema):
    items = schema["properties"]["validation_results"]["items"]
    assert items.get("additionalProperties") is False
    required = set(items["required"])
    props = set(items["properties"].keys())
    assert props == required, f"validation_results.items required mismatch: {props ^ required}"
    assert "command" in required
    assert "exit_code" in required
    assert "stdout" in required
    assert "stderr" in required


def test_validation_results_items_stdout_stderr_nullable(schema):
    items = schema["properties"]["validation_results"]["items"]
    for field in ("stdout", "stderr"):
        t = items["properties"][field].get("type", [])
        assert "null" in t, f"validation_results.items.{field} should allow null"


def test_proposed_followup_tasks_items_strict(schema):
    items = schema["properties"]["proposed_followup_tasks"]["items"]
    assert items.get("additionalProperties") is False
    required = set(items["required"])
    props = set(items["properties"].keys())
    assert props == required, f"proposed_followup_tasks.items required mismatch: {props ^ required}"
    assert "title" in required
    assert "description" in required
