#!/usr/bin/env python3
"""Generate owned observation-parity controls without binary reads or hashing."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from airs.diff import compare_reports
from test_exact_body_candidates import annotated_pair


def serialized(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def finding(report):
    return report["findings"][0]


def evidence():
    return {"code": "owned_observation", "message": "Owned synthetic observation", "address": "0x1008",
            "expected": "recorded-value", "observed": "recorded-value"}


def reason_order(before, after):
    finding(before)["reason_codes"] = ["supported_model_agreement", "owned_reason", "owned_reason"]
    finding(after)["reason_codes"] = list(reversed(finding(before)["reason_codes"]))


def reason_multiplicity(before, after):
    reason_order(before, after)
    finding(after)["reason_codes"] = ["supported_model_agreement", "owned_reason"]


def relocation(before, after):
    for report in (before, after):
        finding(report)["evidence"] = [evidence()]
    delta = 0x4000
    after["image"]["preferred_base"] = hex(int(after["image"]["preferred_base"], 16) + delta)
    item = finding(after)
    for field in ("address", "end_address"):
        item["function"][field] = hex(int(item["function"][field], 16) + delta)
    item["checked_pcs"] = [hex(int(pc, 16) + delta) for pc in item["checked_pcs"]]
    for entry in item["evidence"]:
        entry["address"] = hex(int(entry["address"], 16) + delta)
    for entry in after["metadata_ranges"]:
        for field in ("start", "end"):
            entry[field] = hex(int(entry[field], 16) + delta)


def checked_offset(before, after):
    finding(after)["checked_pcs"] = ["0x100c"]


def checked_order(before, after):
    finding(before)["checked_pcs"] = ["0x1004", "0x1008"]
    finding(after)["checked_pcs"] = ["0x1008", "0x1004"]
    for report in (before, after):
        report["summary"]["checked_pc_count"] = 2


def evidence_bytes(before, after):
    for report in (before, after):
        finding(report)["evidence"] = [evidence()]
    finding(before)["evidence"][0]["expected"] = "cafe\u0301"
    finding(after)["evidence"][0]["expected"] = "caf\u00e9"


def message_only(before, after):
    for report in (before, after):
        finding(report)["evidence"] = [evidence()]
    finding(after)["evidence"][0]["message"] = "Different presentation of the same owned observation"


def controls():
    values = []
    cases = [("reason-order", "unchanged", reason_order),
             ("reason-multiplicity", "changed", reason_multiplicity),
             ("vm-relocation", "unchanged", relocation),
             ("checked-pc-offset", "changed", checked_offset),
             ("checked-pc-order", "changed", checked_order),
             ("evidence-bytes", "changed", evidence_bytes),
             ("message-only", "unchanged", message_only)]
    for name, expected, prepare in cases:
        before, after = annotated_pair()
        for report, label in ((before, "Owned observation baseline"), (after, "Owned observation current")):
            report["generator"].update(version="0.3.3", analysis_model_version="arm64-bounded-test-bit-branch-v50")
            report["image"]["display_name"] = label
            finding(report)["function"]["name"] = "shared_work"
        prepare(before, after)
        result = compare_reports(before, after, match_exact_bodies=False)
        # The expected label comes from the case contract, never from producer output.
        values.append({"name": name, "baselineJSON": serialized(before), "currentJSON": serialized(after),
                       "comparisonJSON": serialized(result), "expectedChange": expected})
    return {"formatVersion": 1, "producer": "airs.diff.compare_reports",
            "limitations": ["Synthetic saved reports and placeholder digests; no binary semantics or authenticity is established."],
            "controls": values}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "native/Tests/AIRSCoreTests/Fixtures/producer-observation-controls-v1.json")
    args = parser.parse_args()
    args.output.write_text(json.dumps(controls(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Wrote seven new owned observation controls")


if __name__ == "__main__":
    main()
