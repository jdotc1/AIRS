# Authentic release case matrix

All 35 cases use arm64, original publisher release ZIPs, and complete actual
archive SHA-256 values in their corresponding case manifests. No binaries are
redistributed. Counts below are supported/total observations and independently
enumerated true-positive/total expected changes; their remainder is unresolved.
No complete-case PASS is claimed. Initial corpus count excludes duplicate source
bytes within a pair and counts prereleases as their actual published versions.

| Case | Publisher | Versions | Attempted/observed strata | Observations | Expected changes | Status |
| --- | --- | --- | --- | ---: | ---: | --- |
| alienator88.pearcleaner.5.4.0-to-5.4.1 | alienator88 | 5.4.0 → 5.4.1 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 121/149 | 8/35 | PARTIAL |
| alienator88.pearcleaner.5.4.1-to-5.4.2 | alienator88 | 5.4.1 → 5.4.2 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 121/149 | 7/31 | PARTIAL |
| alienator88.pearcleaner.5.4.2-to-5.4.3 | alienator88 | 5.4.2 → 5.4.3 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 122/150 | 9/33 | PARTIAL |
| jordanbaird.ice.0.11.11-to-0.11.12 | jordanbaird | 0.11.11 → 0.11.12 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 109/123 | 20/35 | PARTIAL |
| jordanbaird.ice.0.11.12-to-0.11.13-dev.1 | jordanbaird | 0.11.12 → 0.11.13-dev.1 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 120/134 | 34/49 | PARTIAL |
| jordanbaird.ice.0.11.13-dev.1-to-0.11.13-dev.2 | jordanbaird | 0.11.13-dev.1 → 0.11.13-dev.2 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 154/171 | 79/94 | PARTIAL |
| keycastr.keycastr.v0.10.4-to-v0.10.5 | keycastr | v0.10.4 → v0.10.5 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 193/224 | 79/106 | PARTIAL |
| keycastr.keycastr.v0.10.5-to-v0.11.0 | keycastr | v0.10.5 → v0.11.0 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 189/223 | 75/102 | PARTIAL |
| keycastr.keycastr.v0.11.0-to-v0.11.1 | keycastr | v0.11.0 → v0.11.1 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 143/180 | 5/38 | PARTIAL |
| lwouis.alt-tab-macos.v11.10.0-to-v11.10.1 | lwouis | v11.10.0 → v11.10.1 | entitlements, frameworks, loader, privacy_manifest, signature, simple, universal | 79/91 | 5/17 | PARTIAL |
| lwouis.alt-tab-macos.v11.9.1-to-v11.9.2 | lwouis | v11.9.1 → v11.9.2 | entitlements, frameworks, loader, privacy_manifest, signature, simple, universal | 79/91 | 5/17 | PARTIAL |
| lwouis.alt-tab-macos.v11.9.2-to-v11.10.0 | lwouis | v11.9.2 → v11.10.0 | entitlements, frameworks, loader, privacy_manifest, signature, simple, universal | 119/131 | 48/60 | PARTIAL |
| matryer.xbar.v2.1.4-beta-to-v2.1.5-beta | matryer | v2.1.4-beta → v2.1.5-beta | entitlements, loader, privacy_manifest, signature, simple, universal | 22/22 | 5/5 | PARTIAL |
| matryer.xbar.v2.1.5-beta-to-v2.1.6-beta | matryer | v2.1.5-beta → v2.1.6-beta | entitlements, loader, privacy_manifest, signature, simple, universal | 22/22 | 5/5 | PARTIAL |
| matryer.xbar.v2.1.6-beta-to-v2.1.7-beta | matryer | v2.1.6-beta → v2.1.7-beta | entitlements, loader, privacy_manifest, signature, simple, universal | 26/26 | 10/10 | PARTIAL |
| newmarcel.keepingyouawake.1.6.6-to-1.6.7beta1 | newmarcel | 1.6.6 → 1.6.7beta1 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 119/135 | 17/35 | PARTIAL |
| newmarcel.keepingyouawake.1.6.7-to-1.6.8 | newmarcel | 1.6.7 → 1.6.8 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 121/137 | 19/37 | PARTIAL |
| newmarcel.keepingyouawake.1.6.7beta1-to-1.6.7 | newmarcel | 1.6.7beta1 → 1.6.7 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 111/127 | 7/25 | PARTIAL |
| objective-see.knockknock.v4.0.1-to-v4.0.2 | objective-see | v4.0.1 → v4.0.2 | entitlements, loader, privacy_manifest, signature, simple, universal | 23/23 | 5/5 | PARTIAL |
| objective-see.knockknock.v4.0.2-to-v4.0.3 | objective-see | v4.0.2 → v4.0.3 | entitlements, loader, privacy_manifest, signature, simple, universal | 23/23 | 5/5 | PARTIAL |
| objective-see.knockknock.v4.0.3-to-v4.1.0 | objective-see | v4.0.3 → v4.1.0 | entitlements, loader, privacy_manifest, signature, simple, universal | 30/30 | 13/13 | PARTIAL |
| objective-see.oversight.v2.2.1-to-v2.2.2 | objective-see | v2.2.1 → v2.2.2 | entitlements, loader, privacy_manifest, signature, simple, universal | 23/23 | 5/21 | PARTIAL |
| objective-see.oversight.v2.2.2-to-v2.3.0 | objective-see | v2.2.2 → v2.3.0 | entitlements, loader, privacy_manifest, signature, simple, universal | 30/30 | 13/58 | PARTIAL |
| objective-see.oversight.v2.3.0-to-v2.4.0 | objective-see | v2.3.0 → v2.4.0 | entitlements, loader, privacy_manifest, signature, simple, universal | 31/31 | 14/63 | PARTIAL |
| objective-see.taskexplorer.v2.1.0-to-v3.0.0 | objective-see | v2.1.0 → v3.0.0 | entitlements, loader, privacy_manifest, services, signature, simple, universal | 59/61 | 45/45 | PARTIAL |
| objective-see.taskexplorer.v3.0.0-to-v3.1.0 | objective-see | v3.0.0 → v3.1.0 | entitlements, loader, privacy_manifest, signature, simple, universal | 27/27 | 5/10 | PARTIAL |
| p0deje.maccy.2.6.1-to-2.7.0 | p0deje | 2.6.1 → 2.7.0 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 121/135 | 31/46 | PARTIAL |
| p0deje.maccy.2.7.0-to-2.7.1 | p0deje | 2.7.0 → 2.7.1 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 96/110 | 5/20 | PARTIAL |
| p0deje.maccy.2.7.1-to-2.8.0 | p0deje | 2.7.1 → 2.8.0 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 162/176 | 89/104 | PARTIAL |
| sbarex.qlmarkdown.1.5.4-to-1.5.5 | sbarex | 1.5.4 → 1.5.5 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 154/179 | 54/83 | PARTIAL |
| sbarex.qlmarkdown.1.5.5-to-1.5.6 | sbarex | 1.5.5 → 1.5.6 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 126/148 | 7/36 | PARTIAL |
| sbarex.qlmarkdown.1.5.6-to-1.5.7 | sbarex | 1.5.6 → 1.5.7 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 126/148 | 7/36 | PARTIAL |
| swiftbar.swiftbar.v2.1.2-beta-2-to-v2.1.2-beta-3 | swiftbar | v2.1.2-beta-2 → v2.1.2-beta-3 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 114/130 | 4/22 | PARTIAL |
| swiftbar.swiftbar.v2.1.2-beta-3-to-v2.1.2-beta-4 | swiftbar | v2.1.2-beta-3 → v2.1.2-beta-4 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 132/148 | 23/41 | PARTIAL |
| swiftbar.swiftbar.v2.1.2-beta-4-to-v2.1.2-beta-5 | swiftbar | v2.1.2-beta-4 → v2.1.2-beta-5 | entitlements, frameworks, loader, privacy_manifest, services, signature, simple, universal | 114/130 | 5/32 | PARTIAL |

## Stratum attempts

- entitlements: 35/35 distinct cases
- frameworks: 24/35 distinct cases
- loader: 35/35 distinct cases
- privacy_manifest: 35/35 distinct cases
- services: 22/35 distinct cases
- signature: 35/35 distinct cases
- simple: 35/35 distinct cases
- universal: 35/35 distinct cases

Services include physical XPC/extensions and helper candidates; actual inventory
coverage and exclusions remain explicit. Entitlements/signature tags denote
explicit primary-component capture attempts, including unavailable outcomes;
they do not imply every nested component was examined. Privacy tags include
recorded absence as well as present manifests. Loader tags denote captured
declarations, not runtime loading. Source availability did not block acquisition.

Positive/unavailable entitlement coverage is six distinct cases: two actual transitions
(TaskExplorer v2.1.0→v3.0.0 and Ice 0.11.12→0.11.13-dev.1), plus four first helper
captures (Pearcleaner 5.4.0→5.4.1, KeyCastr v0.10.4→v0.10.5, Maccy 2.6.1→2.7.0,
and SwiftBar v2.1.2-beta-2→v2.1.2-beta-3) that explicitly refused as
`source_unavailable` before the entitlement reader. These do not relabel earlier
unexamined helper evidence.
