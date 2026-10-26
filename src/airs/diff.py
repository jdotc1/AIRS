"""Conservative build comparison. Address equality across builds is not identity."""
from __future__ import annotations

from collections import defaultdict

from .report import validate_report
from .types import InputError


def _identity(report: dict) -> dict:
    return {key: report["image"].get(key) for key in ("display_name", "uuid", "slice_sha256", "architecture")}


def _usable_symbol(name: str) -> bool:
    """Adapt MacScope FunctionVersionFingerprinting.isGeneratedName.

    Preserve AIRS's broader historical sub_/address/placeholder exclusions.
    Other donor prefixes are excluded only with a nonempty hexadecimal suffix.
    This withholds matching evidence; it never establishes function identity.
    """
    if not name or name in ('_entry', '__text') or name.startswith(('sub_', '<', '0x', '0X')):
        return False
    for prefix in ('loc_', 'unk_', 'off_', 'nullsub_'):
        if name.startswith(prefix):
            suffix = name[len(prefix):]
            if suffix.startswith(('0x', '0X')): suffix = suffix[2:]
            if suffix and all(char in '0123456789abcdefABCDEF' for char in suffix):
                return False
    return True


def _signature(finding: dict) -> tuple:
    start = int(finding["function"]["address"], 16)
    evidence = tuple((e["code"], e.get("expected"), e.get("observed"), int(e["address"], 16) - start if e.get("address") else None) for e in finding["evidence"])
    return (finding["verdict"], finding["coverage"], finding["mode"], finding["scope"], finding.get("encoding"), tuple(sorted(finding["reason_codes"])), tuple(int(pc, 16) - start for pc in finding["checked_pcs"]), evidence)


def _validated_pairs(pairs, baseline: dict, current: dict, same_image: bool) -> tuple:
    """Adapt MacScope validatedPins: known endpoints, deduplication, bijection."""
    def invalid(message):
        raise InputError('invalid_manual_pair', message)

    if not isinstance(pairs, (list, tuple)) or len(pairs) > 50_000:
        invalid('Manual pairs must be a list or tuple of at most 50,000 ID pairs')
    old_ids = {finding['id'] for finding in baseline['findings']}
    new_ids = {finding['id'] for finding in current['findings']}
    unique = set()
    for item in pairs:
        if (not isinstance(item, (list, tuple)) or len(item) != 2
                or not all(isinstance(endpoint, str) for endpoint in item)):
            invalid('Each manual pair requires baseline and current finding IDs')
        old, new = item
        if old not in old_ids or new not in new_ids:
            invalid('Manual pair endpoints must exist in their respective selected reports')
        unique.add((old, new))
    ordered = tuple(sorted(unique))
    if ordered and same_image:
        invalid('Exact-image offset matching is authoritative; manual pairs require different images')
    used_old, used_new = set(), set()
    for old, new in ordered:
        if old in used_old or new in used_new:
            invalid('Manual pairs must be one-to-one; conflicting endpoints are not accepted')
        used_old.add(old); used_new.add(new)
    return ordered


def _body_candidates(groups: dict) -> set:
    """Adapt MacScope's snapshot-based unique-key phase without guessing ties.

    Established pairs and ambiguous symbol groups retain precedence. Count all
    remaining fingerprints, including blocked ambiguous groups, before selecting
    any candidate. A single bounded phase deliberately avoids fixpoint expansion.
    """
    buckets = defaultdict(lambda: {'before': [], 'after': []})
    eligible = set()
    for group in groups.values():
        if len(group['before']) == len(group['after']) == 1:
            continue
        standalone = len(group['before']) + len(group['after']) == 1
        for side in ('before', 'after'):
            for finding in group[side]:
                fingerprint = finding['function'].get('body_fingerprint')
                if fingerprint is None:
                    continue
                key = (fingerprint['kind'], fingerprint['sha256'], fingerprint['instruction_count'])
                buckets[key][side].append(finding)
                if standalone: eligible.add((side, finding['id']))
    selected, ambiguous = {}, set()
    consumed = {'before': set(), 'after': set()}
    for key, group in buckets.items():
        if len(group['before']) == len(group['after']) == 1:
            old, new = group['before'][0], group['after'][0]
            if ('before', old['id']) not in eligible or ('after', new['id']) not in eligible:
                continue
            selected['body:'+':'.join(map(str, key))] = group
            consumed['before'].add(old['id']); consumed['after'].add(new['id'])
        elif group['before'] and group['after']:
            ambiguous.update((side, finding['id']) for side in ('before', 'after') for finding in group[side])
    for key in list(groups):
        group = groups[key]
        for side in ('before', 'after'):
            group[side] = [finding for finding in group[side] if finding['id'] not in consumed[side]]
        if not group['before'] and not group['after']: del groups[key]
    groups.update(selected)
    return ambiguous


def compare_reports(baseline: dict, current: dict, *, manual_pairs=(), match_exact_bodies: bool = False) -> dict:
    if type(match_exact_bodies) is not bool:
        raise InputError('invalid_matching_option', 'Exact-body matching requires a boolean opt-in')
    validate_report(baseline)
    validate_report(current)
    same_image = baseline["image"]["slice_sha256"] == current["image"]["slice_sha256"] and baseline["image"]["architecture"] == current["image"]["architecture"]
    pairs = _validated_pairs(manual_pairs, baseline, current, same_image)
    manual_before = {old: f'manual:{old}:{new}' for old, new in pairs}
    manual_after = {new: f'manual:{old}:{new}' for old, new in pairs}
    compatible = baseline["generator"]["analysis_model_version"] == current["generator"]["analysis_model_version"] and baseline["image"]["architecture"] == current["image"]["architecture"]
    configuration_changed = baseline.get("analysis_config") != current.get("analysis_config")
    groups: dict[str, dict[str, list]] = defaultdict(lambda: {"before": [], "after": []})

    for side, report in (("before", baseline), ("after", current)):
        for finding in report["findings"]:
            function = finding["function"]
            manual = manual_before if side == 'before' else manual_after
            if finding['id'] in manual:
                key = manual[finding['id']]
            elif same_image:
                key = "offset:" + hex(int(function["image_offset"], 16))
            elif _usable_symbol(function["name"]):
                key = "symbol:" + function["name"]
            else:
                # A stripped function has no reliable cross-build join key yet.
                key = f"unmatched:{side}:{finding['id']}"
            groups[key][side].append(finding)

    body_ambiguities = set()
    if (match_exact_bodies and not same_image
            and baseline['image']['architecture'] == current['image']['architecture']
            and baseline['image']['cpu_subtype'] == current['image']['cpu_subtype']):
        body_ambiguities = _body_candidates(groups)

    summary = {"matched_count": 0, "changed_count": 0, "unchanged_count": 0, "added_count": 0, "removed_count": 0, "ambiguous_count": 0}
    changes: list[dict] = []
    for key in sorted(groups):
        before_group, after_group = groups[key]["before"], groups[key]["after"]
        before = before_group[0] if len(before_group) == 1 else None
        after = after_group[0] if len(after_group) == 1 else None
        notes: list[str] = []
        basis = "manual_review" if key.startswith("manual:") else "exact_image_offset" if key.startswith("offset:") else "unique_symbol" if key.startswith("symbol:") else "exact_body_candidate" if key.startswith("body:") else "unmatched"
        if len(before_group) > 1 or len(after_group) > 1:
            change = "ambiguous"
            notes.append(f"This key has {len(before_group)} baseline and {len(after_group)} current candidates; none was selected automatically.")
        elif before is not None and after is not None:
            summary["matched_count"] += 1
            if not compatible:
                change = "ambiguous"
                notes.append("Analysis model or architecture differs. Reanalyze both inputs with one model before interpreting a verdict change.")
            elif configuration_changed:
                change = "ambiguous"
                notes.append("Analysis configuration differs or is missing from one report. Reanalyze both inputs with one configuration before interpreting a finding change.")
            else:
                change = "unchanged" if _signature(before) == _signature(after) else "changed"
            if basis == 'exact_body_candidate':
                notes.append('Unique exact-byte body fingerprint is a review candidate; it does not prove source-function identity or a regression/fix. Imported digests are not authenticated and relocations may change encoded bytes.')
            if basis == 'manual_review':
                notes.append('User-selected finding pair is a review candidate; it does not prove source-function identity or a regression/fix.')
            if basis == "unique_symbol":
                notes.append("Unique symbol-name match is a review candidate; it does not prove source-function identity across builds.")
        elif after is not None:
            change = "added"
            notes.append("No accepted baseline match; this may be a newly named, moved or previously stripped function.")
        else:
            change = "removed"
            notes.append("No accepted current match; absence is not a fixed finding.")
        if any((side, finding['id']) in body_ambiguities
               for side, members in (('before', before_group), ('after', after_group)) for finding in members):
            notes.append('Exact-body fingerprint is not unique on both remaining sides; no body pair was selected.')
        summary[change + "_count"] += 1
        representative = after or before or (after_group or before_group)[0]
        row = {"key": key, "match_basis": basis, "function_name": representative["function"]["name"], "change": change, "notes": notes}
        for prefix, value in (("baseline", before), ("current", after)):
            if value is not None:
                row[prefix + "_id"] = value["id"]
        if before is not None:
            row.update(before_verdict=before["verdict"], before_scope=before["scope"])
        if after is not None:
            row.update(after_verdict=after["verdict"], after_scope=after["scope"])
        changes.append(row)

    limitations = ["Different build addresses are never joined solely because they are equal.", "Cross-build symbol matches are candidates for review, not guaranteed source identity.", "Generated address labels and generic entry/section labels provide no cross-build matching evidence.", "Added/removed unmatched functions are not automatically regressions/fixes.", "An agreement still has the scope and limitations of its source report."]
    if configuration_changed:
        limitations.append("Analysis configuration differs or is missing from one report; budget-related scope changes require review.")
    result = {"schema_version": 1, "report_kind": "airs.diff", "comparison": {"baseline_image": _identity(baseline), "current_image": _identity(current), "same_image": same_image, "model_compatible": compatible, "analysis_configuration_changed": configuration_changed, "matching_policy": "exact_digest_then_unique_symbol", "exact_body_candidates": match_exact_bodies}, "summary": summary, "changes": changes, "limitations": limitations}
    if pairs:
        result['comparison']['matching_policy'] = 'manual_then_unique_symbol'
        result['comparison']['manual_pairs'] = [
            {'baseline_id': old, 'current_id': new} for old, new in pairs]
        result['limitations'].append('Manual pairs record user selection, not independently established cross-build function identity.')
    if match_exact_bodies:
        result['comparison']['matching_policy'] += '_then_exact_body_candidate'
        result['limitations'].append('Exact-body candidates require unique eligible evidence on both remaining sides and equal CPU subtype; existing pairs and ambiguous symbol groups retain precedence. A digest match is review evidence, not source-function identity.')
    return result
