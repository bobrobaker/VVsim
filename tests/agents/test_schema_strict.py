"""Verify that .agents/schemas/implementation_result.json satisfies OpenAI strict
structured-output requirements: every object schema must have additionalProperties: false,
including nested objects inside array items."""

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
    if node.get("type") == "object":
        yield path, node
    # Recurse into properties values
    for key, child in node.get("properties", {}).items():
        yield from _collect_object_schemas(child, f"{path}.properties.{key}")
    # Recurse into array items
    items = node.get("items")
    if isinstance(items, dict):
        yield from _collect_object_schemas(items, f"{path}.items")
    # Recurse into anyOf / oneOf / allOf
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
                f"{path}: additionalProperties={obj_schema.get('additionalProperties', '<missing>')!r}"
            )
    assert not violations, (
        "Object schemas missing 'additionalProperties: false':\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_no_open_metadata_field(schema):
    """metadata field must not exist as an open-ended object in the schema."""
    props = schema.get("properties", {})
    assert "metadata" not in props, (
        "Schema contains a 'metadata' field — open-ended metadata is incompatible "
        "with OpenAI strict structured output. Remove it or convert to a closed schema."
    )


def test_required_fields_present(schema):
    required = schema.get("required", [])
    assert "task_id" in required
    assert "status" in required
    assert "summary" in required


def test_status_enum_values(schema):
    status = schema["properties"]["status"]
    assert set(status["enum"]) == {"success", "partial", "failed", "skipped"}


def test_validation_results_items_strict(schema):
    items = schema["properties"]["validation_results"]["items"]
    assert items.get("additionalProperties") is False
    assert "command" in items["required"]
    assert "exit_code" in items["required"]


def test_proposed_followup_tasks_items_strict(schema):
    items = schema["properties"]["proposed_followup_tasks"]["items"]
    assert items.get("additionalProperties") is False
    assert "title" in items["required"]
    assert "description" in items["required"]
