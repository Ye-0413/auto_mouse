from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class RowIssue:
    data_row_index: int
    """1-based index among data rows (first data row == 1)."""
    messages: list[str] = field(default_factory=list)


def validate_rows(
    headers: list[str],
    rows: list[list[str]],
    *,
    primary_key_header: str | None,
    mapped_columns: list[str] | None = None,
) -> list[RowIssue]:
    """
    Validate rows used for preview (or full data). Checks empties for mapped
    columns and duplicate primary keys when ``primary_key_header`` is set.
    """
    mapped = mapped_columns if mapped_columns is not None else headers
    header_index = {h: i for i, h in enumerate(headers)}
    pk_idx = header_index.get(primary_key_header) if primary_key_header else None

    issues_by_row: dict[int, RowIssue] = {}
    seen_pk: dict[str, int] = {}

    for r_i, row in enumerate(rows, start=1):
        msgs: list[str] = []
        row_vals = list(row) + [""] * (len(headers) - len(row))

        for col in mapped:
            if col not in header_index:
                continue
            ci = header_index[col]
            val = row_vals[ci].strip() if ci < len(row_vals) else ""
            if not val:
                msgs.append(f"列为空：{col}")

        if primary_key_header and pk_idx is not None:
            pk_val = row_vals[pk_idx].strip() if pk_idx < len(row_vals) else ""
            if not pk_val:
                msgs.append(f"主键为空：{primary_key_header}")
            else:
                prev = seen_pk.get(pk_val)
                if prev is not None:
                    msgs.append(f"主键重复：{primary_key_header}={pk_val!r}（第 {prev} 行）")
                else:
                    seen_pk[pk_val] = r_i

        if msgs:
            issues_by_row[r_i] = RowIssue(data_row_index=r_i, messages=msgs)

    return [issues_by_row[k] for k in sorted(issues_by_row)]
