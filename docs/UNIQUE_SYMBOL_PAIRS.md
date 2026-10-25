# Native evidence for selected unique-symbol pairs

Baseline: public main 1b778a2, exact-image offset validation merged in public PR7.
This bounded increment adapts MacScope FunctionVersionMatcher's manual-pin
precedence and unique-key/no-guess pattern to AIRS's existing Python symbol phase.
The precise usable-name policy and snapshot phase order remain AIRS host behavior;
the donor's iterative body/CFG/call propagation is not imported. MacScope remains
read-only and no framework/dependency is added.

## Explicit API and selected-pair rules

ComparisonReport.validateUniqueSymbolPairs(baselineData:currentData:) composes
validateExactImageOffsetRows, retaining prior accounting, selected-source facts,
manual selection, compatibility, observation labels and exact-image authority.
Same-image comparisons retain their offset-only rule; no symbol override is added.

For cross-image rows with basis unique_symbol and both selected IDs, the helper
requires the source findings to have exact, usable names. Grouping and comparison
use UTF-8 bytes without case folding, trimming or canonical Unicode equivalence.
The row key must be exactly symbol: followed by the source name's raw bytes.
Display names and imported row labels do not substitute for source name evidence.

Only endpoints in recorded, validated manual pairs are removed before grouping.
Each selected name must then identify one remaining baseline finding and one
remaining current finding, exactly the selected IDs. Omitted findings remain in
those groups and can block uniqueness. Imported body/future matching rows cannot
remove duplicate blockers. Unrecorded manual selections are not invented from
missing metadata, and manual-pair fields retain their existing optional meaning.

The usable-name policy preserves the host's broader exclusions: missing/empty
names, generic entry/section names, every sub_ prefix, placeholder/address prefixes,
and the donor-style loc_/unk_/off_/nullsub_ prefixes with nonempty ASCII-hex suffixes
withhold evidence. Optional hexadecimal markers retain their existing meaning.
Empty/nonhex donor suffixes and case-sensitive boundary cases follow Python's
policy; the helper does not broaden exclusions or use Unicode isHexDigit behavior.
Raw byte prefixes preserve the rule even when combining marks adjoin a prefix.

Established one-to-one symbol groups are preserved before Python's body phase.
Consequently absent, false or true exact_body_candidates metadata does not alter
this selected-pair proof. The helper does not invent false for an absent flag or
change that metadata; it does not need to infer the body phase's setting.

## Limits of success

Uniqueness establishes a review candidate, not source-function identity across
builds. Imported names/digests are not authenticated against original binaries.
Observation compatibility and changed/unchanged labels remain separate facts,
verified here only through the existing composed path.

One-sided/ambiguous symbol rows without both selected IDs remain outside this new
symbol proof. Body and future basis semantics are not checked, and omitted matches
or source findings are not discovered. Empty comparisons and deliberately
unselected groups may pass without implying completeness. This is not full symbol
phase reconstruction, a new matcher, or the donor's fixpoint algorithm.

Original immutable Data retains the existing 64 MiB per-source, finding-count and
row bounds. The composed validators perform several bounded parsing passes;
source grouping and row lookup use bounded maps with raw name-byte processing.
No file, image, runtime or store is opened, executed, hashed, mutated or written.
Native targets remain macOS 14+, schema 1 and engine model v50. Default decoding,
matching production and GUI workflows do not automatically invoke this strict API.

## Qualification

Fourteen new UniqueSymbolPairsTests methods passed with zero failures in 0.066
seconds. The real AIRSApp debug product built successfully in 17.00 seconds under
the exclusive native gate. The first preimplementation compile reported the
expected missing API and ran no runtime test method. Accepted unchanged exact-
image, matched/manual, source, accounting, codec, Python, GUI and distribution
results were reused rather than replayed.

Coverage includes valid pairs, different source names, omitted duplicate blockers,
manual-pin precedence and required metadata, untrusted body-claim consumption,
generated/generic names, empty/nonhex suffixes, combining prefix boundaries,
case/whitespace/Unicode distinctions, exact keys, body-flag preservation,
configuration/source prerequisites, same-image authority, missing names and the
explicit one-sided/other-basis/completeness boundaries. Inputs are small synthetic
reports with placeholder digests, not user data or a binary corpus.

Independent read-only source/test review found no actionable defect and confirmed
host policy parity and conservative duplicate handling. Detailed logs remain
private; generated build products are removed after retaining receipts. Build
success is not GUI or installed-app acceptance.

No packaging, signing, installation, production settings/store change or MacScope
mutation is claimed by this qualification. Installed app, settings and stores
remain unchanged; public integration does not activate native workflows.
