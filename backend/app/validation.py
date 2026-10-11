from datetime import date

from .errors import ApiError

INT_MAX = 2_147_483_647  # PostgreSQL INTEGER upper bound


def validate(spec, data, partial=False):
    """spec: {field: dict(type, required, choices, max, min, fk)}. Returns cleaned dict or raises 422."""
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object", 400)
    out, errors = {}, {}
    for name, rule in spec.items():
        if name not in data:
            if rule.get("required") and not partial:
                errors[name] = "is required"
            continue
        v = data[name]
        t = rule.get("type", "str")
        if v in (None, "") and not rule.get("required"):
            out[name] = None if t in ("date", "int", "fk") or rule.get("nullable") else ""
            continue
        try:
            if t == "str":
                if not isinstance(v, str):
                    raise ValueError("must be a string")
                v = v.strip()
                if rule.get("required") and not v:
                    raise ValueError("must not be empty")
                if len(v) > rule.get("max", 100000):
                    raise ValueError(f"must be at most {rule['max']} characters")
            elif t in ("int", "fk"):
                if isinstance(v, bool) or not isinstance(v, int):
                    if isinstance(v, str) and v.lstrip("-").isdigit():
                        v = int(v)
                    else:
                        raise ValueError("must be an integer")
                if "min" in rule and v < rule["min"]:
                    raise ValueError(f"must be >= {rule['min']}")
                if v > rule.get("max", INT_MAX):
                    raise ValueError(f"must be <= {rule.get('max', INT_MAX)}")
            elif t == "date":
                v = date.fromisoformat(v)
            elif t == "bool":
                if not isinstance(v, bool):
                    raise ValueError("must be true or false")
            if "choices" in rule and v not in rule["choices"]:
                raise ValueError(f"must be one of {', '.join(rule['choices'])}")
        except (ValueError, TypeError) as e:
            errors[name] = str(e) if "must" in str(e) else "invalid value (dates use YYYY-MM-DD)" if t == "date" else str(e)
            continue
        out[name] = v
    if errors:
        raise ApiError("Validation failed", 422, errors)
    return out
