# Security delta review: evidence semantics

Independent review found that equal recorded slice digests could coexist with
contradictory signature presence or retained signature ranges. The analyzer
now reports the contradiction as unresolved and withholds dependent claims.
Synthetic regression tests cover conflicting presence, ranges, and retained
bytes. Incomplete and unsupported signature evidence remains distinct from
recorded absence; signature trust and runtime behavior are outside scope.
