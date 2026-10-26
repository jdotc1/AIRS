#!/usr/bin/env python3
"""Generate bounded synthetic producer/native integration controls; no binary reads."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from airs.diff import compare_reports
from test_exact_body_candidates import annotated_pair
from test_diff_manual_pairs import second, A, B, C, D


def serialized(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"))


def controls():
    values = []

    def add(name, bases, rows, setting=False, pins=(), prepare=None):
        before, after = annotated_pair()
        for report, label in ((before, "Owned baseline"), (after, "Owned current")):
            report["generator"].update(version="0.3.3", analysis_model_version="arm64-bounded-test-bit-branch-v50")
            report["image"]["display_name"] = label
        if prepare:
            prepare(before, after)
        comparison = compare_reports(before, after, manual_pairs=pins, match_exact_bodies=setting)
        # Expectations are supplied independently, never copied from the result.
        values.append({"name": name, "baselineJSON": serialized(before), "currentJSON": serialized(after),
                       "comparisonJSON": serialized(comparison), "expectedBases": bases,
                       "expectedRows": rows, "expectedBodyStatus": setting})

    def extra_stripped(before, after):
        second(before, C, "sub_1010"); second(after, D, "loc_2010")

    def same_image(before, after):
        after["image"]["slice_sha256"] = before["image"]["slice_sha256"]

    def unicode_symbols(before, after):
        for report, identifier in ((before, C), (after, D)):
            report["findings"][0]["function"]["name"] = "cafe\u0301"
            second(report, identifier, "caf\u00e9")

    def blocked(before, after):
        second(before, C, "sub_1010")

    add("default-disabled", ["unmatched"], 2)
    add("body-enabled", ["exact_body_candidate"], 1, setting=True)
    add("manual-disabled", ["manual_review"], 1, pins=[(A, B)])
    add("manual-body-enabled", ["exact_body_candidate", "manual_review"], 2,
        setting=True, pins=[(A, B)], prepare=extra_stripped)
    add("same-image-disabled", ["exact_image_offset"], 1, prepare=same_image)
    add("same-image-enabled", ["exact_image_offset"], 1, setting=True, prepare=same_image)
    add("unicode-symbols", ["unique_symbol"], 2, prepare=unicode_symbols)
    add("duplicate-body-blockers", ["unmatched"], 3, setting=True, prepare=blocked)
    return {"formatVersion": 1, "producer": "airs.diff.compare_reports",
            "limitations": ["Synthetic saved reports only; digest and fingerprint values are placeholders, not authenticated evidence."],
            "controls": values}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "native/Tests/AIRSCoreTests/Fixtures/producer-coverage-controls-v1.json")
    args = parser.parse_args()
    args.output.write_text(json.dumps(controls(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Wrote eight owned producer coverage controls")


if __name__ == "__main__":
    main()
