from __future__ import annotations


def build_variable_map_default(headers: list[str]) -> dict[str, str]:
    """One-to-one mapping: column title -> variable name (same string)."""
    out: dict[str, str] = {}
    for h in headers:
        key = h.strip()
        if not key:
            continue
        out[key] = key
    return out


def row_to_variables(
    headers: list[str],
    row_values: list[str],
    variable_map: dict[str, str],
) -> dict[str, str]:
    """
    Build runtime variables for one row. Only mapped columns with a non-empty
    variable name are included.
    """
    width = max(len(headers), len(row_values))
    padded_values = list(row_values) + [""] * (width - len(row_values))
    row_by_header = {
        headers[i]: padded_values[i]
        for i in range(min(len(headers), len(padded_values)))
    }
    out: dict[str, str] = {}
    for header, var_name in variable_map.items():
        name = var_name.strip()
        if not name:
            continue
        out[name] = str(row_by_header.get(header, "")).strip()
    return out
