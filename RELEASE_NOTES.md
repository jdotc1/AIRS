# AIRS 0.3.3 Preview — build 10

Build 10 adds an explicit isolated acceptance profile. It displays real report and
comparison views using owned fixtures, fresh preferences and app-owned storage,
non-recording recents, and a native window with restoration disabled. Native file
panels and external exports are unavailable in this bounded profile. Ordinary
launches retain the existing application path; engine semantics are unchanged.

The accepted Apple silicon candidate is Developer ID signed, notarized and stapled.
Its browser-downloaded copy completed GUI launch and actual App Translocation
acceptance in this profile. Report display, comparison-sheet display/dismissal,
and normal window-close termination were observed. Production app and data
metadata were unchanged. Existing engine and comparison regression results are
reused; no fresh CI pass or repeated unchanged-suite result is claimed.

See [release evidence and limits](docs/RELEASE_0_3_3_BUILD10.md) and the
[isolated profile contract](docs/ISOLATED_ACCEPTANCE_PROFILE.md).
Clean-machine, minimum-macOS, Intel-app and offline qualification remain incomplete.
Earlier release assets remain available.
