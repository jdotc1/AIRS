# Release history reconciliation — October 25, 2026

The repository cleanup rewrote release source identities and regenerated the source
archives for five releases. The current repository is `jdotc1/AIRS`. Original
qualification and download-acceptance receipts remain historical evidence; their
old source revisions must be interpreted using the mapping below. They have not
been rewritten to imply that the cleaned source was executed or qualified.

The [structured supplement](qualification/RELEASE_HISTORY_RECONCILIATION_2026_10_25.json)
records full original and rewritten commit/tag identities, original and regenerated
source ZIP SHA-256 values, and accepted app archive SHA-256 values. These are copied
from the retained cleanup records, not newly calculated checksums.

| Release | Original source revision | Rewritten source revision |
| --- | --- | --- |
| v0.3.2 | `3a30d7a7872cebd48babe4485bbe47ccb908c1eb` | `25bfbf1a162be3c4b5d98477082bb42fe31e9070` |
| v0.3.3 | `b61f26e52ca9b42789943b4d7f7f0c360ee3c1c9` | `a49974fd1262e37ec1052ae0f00d396fa7f30150` |
| v0.3.3-build9 | `1e4a76f4f4d710bf88afd643345d04ee21d8b9a0` | `3bb60d39be330e8345db50168eb692a2fd38cf00` |
| v0.3.3-build10 | `31d9ef4741ff975942aa14368dd0381f6180cd26` | `e8db379e7af95c11dedd620f5f660afde00e81a7` |
| v0.3.3-build12 | `9babe4f7bfc6132e6eb97cfec40af500efb7bd1c` | `0c2993fdf98ddf2d6a34b2b15fa27238bfa01c06` |

For annotated tags the supplement distinguishes the tag object from its peeled
source commit. Build 9 uses a lightweight tag, so those identities coincide.

## Scope of retained evidence

The cleanup checksum records retain the same app archive identities for all five
releases. Existing build, signing, notarization, stapling and workflow acceptance
therefore remain accepted for those app payloads within their original limits.
No app rebuild, signing check, archive rehash or test was repeated for this record.

Every regenerated source ZIP has a different recorded checksum. Historical claims
of unchanged implementation Git objects or source ZIP byte identity apply to the
original publication, not automatically to the rewritten source. Mapping history
establishes lineage; it does not establish source equivalence, successful behavior
of changed path configuration, or reproducibility of the retained app from the
cleaned source. Source-path repair and its qualification are separate work.

The build 12 download-acceptance supplement still records the accepted app transfer
and isolated launch. Its original `release_source_revision` and statement that the
source ZIP/checksums remained unchanged describe the October 24 record publication;
they do not describe the subsequent cleanup. Its app archive digest remains the
accepted one. Original qualification JSON assets keep their historical source
fields; use this supplement instead of silently replacing those fields.

## Repository references and publication status

Repository links in maintained release prose now use `jdotc1/AIRS`. Historical
receipts may retain `AIRS-app` URLs and original revisions; those are original
observations, not current download instructions. Earlier pull-request URLs may no
longer resolve to the original records after repository recreation.

This supplement reuses accepted cleanup evidence and records its limits. It does
not assert that remote assets were checked again, that all publication surfaces
are cleared, or that the changed source paths have passed runtime acceptance.
No remote changes, app installation or store changes are part of this local record
reconciliation. Existing release and publication gates remain in force.
