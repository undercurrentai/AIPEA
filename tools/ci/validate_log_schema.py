# validate_log_schema.py — Validate *.log.json files against log event schema.
# Stdlib-only. Exit 0 on pass/skip, exit 1 on failure.
#
# Validation layers (all derived dynamically from the schema):
#   1. JSON object check
#   2. Required fields present
#   3. No additional properties (if additionalProperties: false)
#   4. Type validation per field (handles union types like ["string", "null"])
#   5. Enum validation for fields with enum constraints

import json, sys, pathlib

# --- Schema loading -----------------------------------------------------------

schema_path = pathlib.Path("schemas/log_event.schema.json")
if not schema_path.exists():
    print("SKIP: No log schema found."); sys.exit(0)

try:
    schema = json.loads(schema_path.read_text())
except (json.JSONDecodeError, OSError) as e:
    print(f"FAIL: Cannot parse {schema_path}: {e}")
    sys.exit(1)

if not isinstance(schema, dict):
    print(f"FAIL: {schema_path} must be a JSON object, got {type(schema).__name__}")
    sys.exit(1)

# --- Build validation rules from schema ---------------------------------------

required_fields = set(schema.get("required", []))
properties = schema.get("properties", {})
additional_allowed = schema.get("additionalProperties", True)
known_keys = set(properties.keys())

# JSON Schema type -> Python type(s).  bool check must come before int
# because isinstance(True, int) is True in Python.
_JSON_TO_PYTHON = {
    "string": (str,),
    "number": (int, float),
    "integer": (int,),
    "boolean": (bool,),
    "null": (type(None),),
    "object": (dict,),
    "array": (list,),
}


def _allowed_types(type_spec):
    """Return tuple of Python types allowed by a JSON Schema 'type' value."""
    if isinstance(type_spec, str):
        return _JSON_TO_PYTHON.get(type_spec, ())
    if isinstance(type_spec, list):
        result = []
        for t in type_spec:
            if isinstance(t, str):
                result.extend(_JSON_TO_PYTHON.get(t, ()))
        return tuple(result)
    return ()


def _check_type(value, type_spec):
    """Return True if value matches the JSON Schema type spec."""
    allowed = _allowed_types(type_spec)
    if not allowed:
        return True  # unknown type spec — skip validation
    # bool trap: if bool is not in the allowed set but int is, reject booleans
    if isinstance(value, bool) and bool not in allowed:
        return False
    return isinstance(value, allowed)


# Pre-compute per-field rules
field_types = {}   # field_name -> type spec (str or list)
field_enums = {}   # field_name -> set of allowed values

for fname, fschema in properties.items():
    if not isinstance(fschema, dict):
        continue
    if "type" in fschema:
        field_types[fname] = fschema["type"]
    if "enum" in fschema and isinstance(fschema["enum"], list):
        field_enums[fname] = set(fschema["enum"])

# --- Validate log files -------------------------------------------------------

violations = 0

for p in pathlib.Path(".").rglob("*.log.json"):
    try:
        data = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        print(f"FAIL: Bad JSON in {p}: {e}")
        violations += 1
        continue
    except OSError as e:
        print(f"FAIL: Cannot read {p}: {e}")
        violations += 1
        continue

    if not isinstance(data, dict):
        print(f"FAIL: {p} is not a JSON object")
        violations += 1
        continue

    entry_bad = False

    # Layer 2: required fields
    missing = required_fields - set(data.keys())
    if missing:
        print(f"FAIL: {p} missing required fields: {sorted(missing)}")
        entry_bad = True

    # Layer 3: additionalProperties
    if not additional_allowed:
        extra = set(data.keys()) - known_keys
        if extra:
            print(f"FAIL: {p} has unexpected fields: {sorted(extra)}")
            entry_bad = True

    # Layer 4: type validation
    for fname, value in data.items():
        if fname in field_types:
            if not _check_type(value, field_types[fname]):
                expected = field_types[fname]
                actual = type(value).__name__
                print(f"FAIL: {p} field '{fname}' has type {actual}, expected {expected}")
                entry_bad = True

    # Layer 5: enum validation
    for fname, allowed_vals in field_enums.items():
        if fname in data and data[fname] is not None:
            if data[fname] not in allowed_vals:
                print(f"FAIL: {p} field '{fname}' value '{data[fname]}' not in {sorted(allowed_vals)}")
                entry_bad = True

    if entry_bad:
        violations += 1

if violations:
    sys.exit(1)
print("OK: Log schema validation passed.")
