"""Bounded terminal presentation of an existing supplied-report inventory."""
from __future__ import annotations

from .report import MAX_REPORT_BYTES
from .report_summary_text import _BoundedText
from .types import InputError

MAX_REASON_ROWS = 32
MAX_EXAMPLES_PER_REASON = 3


def render_coverage_text(inventory: dict, *, maximum_bytes: int = MAX_REPORT_BYTES) -> str:
    """Render inventory facts without changing aggregation or evidence meaning.

    Every saved value and object key uses ASCII JSON escaping. Output is built
    incrementally and returned only when complete, including its final newline.
    """
    if type(maximum_bytes) is not int or maximum_bytes < 0:
        raise InputError("invalid_report_size_limit", "Coverage text byte limit must be a nonnegative integer")
    maximum_bytes = min(maximum_bytes, MAX_REPORT_BYTES)
    chunks: list[str] = []
    used = 0

    def append(chunk: str) -> None:
        nonlocal used
        used += len(chunk.encode("utf-8"))
        if used > maximum_bytes:
            raise InputError("generated_report_size_limit",
                             "Generated coverage text exceeds the report size limit; no partial report was written")
        chunks.append(chunk)

    def line(label: str, value: object) -> None:
        append(label + ": ")
        # Reuse the summary renderer's escaped-size preflight. iterencode can
        # allocate an entire expanded string before yielding its first chunk.
        try:
            quoted = _BoundedText(maximum_bytes - used).quoted(value)
        except InputError as exc:
            raise InputError("generated_report_size_limit",
                             "Generated coverage text exceeds the report size limit; no partial report was written") from exc
        append(quoted)
        append("\n")

    append("AIRS saved-report coverage inventory\n")
    append("Supplied saved reports only; this is not real-world prevalence.\n")
    append("Duplicate reports count once; conflicting variants count separately.\n")
    append("Reason counts may overlap for the same unresolved finding.\n")
    line("Status", inventory["status"])
    line("Summary (full inventory denominators)", inventory["summary"])
    line("Models (nonduplicate report counts)", inventory["models"])
    line("Conflicting report indices", inventory["conflicting_report_indices"])
    if "reason_selection" in inventory:
        line("Reason selection (does not filter denominators)", inventory["reason_selection"])
    else:
        append("Reason selection: all inventory reasons\n")
    if "reason_frequency_selection" in inventory:
        line("Reason frequency selection (does not filter denominators)", inventory["reason_frequency_selection"])
    if "reason_order" in inventory:
        line("Reason order", inventory["reason_order"])
    if "reason_limit" in inventory:
        line("Reason limit (does not filter denominators)", inventory["reason_limit"])
    append("Reports (all supplied inputs, including duplicates and conflicts)\n")
    for record in sorted(inventory["reports"], key=lambda row: row["index"]):
        line("Report", record)
    reasons = (sorted(inventory["reasons"], key=lambda row: row["reason"])
               if inventory.get("reason_order") == "reason" else
               sorted(inventory["reasons"], key=lambda row: (-row["count"], row["reason"])))
    line("Reason rows available", len(reasons))
    for reason in reasons[:MAX_REASON_ROWS]:
        line("Reason", {"reason": reason["reason"], "count": reason["count"]})
        examples = reason["examples"][:MAX_EXAMPLES_PER_REASON]
        for example in examples:
            line("  Example", example)
        # Inventory stores at most eight examples; count includes uncaptured ones.
        line("  Examples omitted (including inventory sampling)", max(0, reason["count"] - len(examples)))
    line("Reason rows omitted", max(0, len(reasons) - MAX_REASON_ROWS))
    for limitation in inventory["limitations"]:
        line("Limitation", limitation)
    return "".join(chunks)
