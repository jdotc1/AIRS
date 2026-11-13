"""Synthetic thin ARM64 images for the broad-extended-v3 tests. Words are hand encoded from the Arm
Architecture Reference Manual (shape_word_helpers); no image is executed, signed or loaded."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shape_word_helpers import blr, ldr, ldur, ret  # noqa: E402
from stub_image_helpers import Import, build_stub_image  # noqa: E402

IMPORTED_ACCESSOR = '_$sSS10FoundationE8EncodingVMa'
LOCAL_ACCESSOR_NAME = b'_$sSiMa'           # padded with NUL to the length of the generated name _caller1
RUNTIME_METADATA = '_swift_getGenericMetadata'
OTHER_FUNCTION = '_$s4Test3fooyS2iF'
# Table load -8 from x0 and a function slot (+0x8) load, then the indirect call.
WITNESS_TAIL = (ldur(8, 0, -8), ldr(8, 8, 8), blr(8), ret())


def imported_metadata(symbol):
    """caller0: bl <import stub 0>; value witness call through x0."""
    return build_stub_image(callers=((('bl', ('stub', 0)), *WITNESS_TAIL),), imports=(Import(symbol, 1),))[0]


def local_accessor():
    """caller0 calls caller1, renamed to a metadata accessor symbol, then calls a value witness."""
    probe = build_stub_image(callers=((('bl', 0), *WITNESS_TAIL), (ret(),)))[1]
    data, layout = build_stub_image(callers=((('bl', probe.caller_addrs[1]), *WITNESS_TAIL), (ret(),)))
    assert data.count(b'_caller1\0') == 1
    return data.replace(b'_caller1\0', LOCAL_ACCESSOR_NAME + b'\0\0')


def local_unnamed_callee():
    """Same shape with the callee keeping its generated name: no symbol knowledge."""
    probe = build_stub_image(callers=((('bl', 0), *WITNESS_TAIL), (ret(),)))[1]
    return build_stub_image(callers=((('bl', probe.caller_addrs[1]), *WITNESS_TAIL), (ret(),)))[0]


def closure_context():
    """An indirect call whose table register comes from x20, not from a value witness table."""
    return build_stub_image(callers=((ldr(8, 20, 16), blr(8), ret()),))[0]


def isa_load():
    """Metadata from an object's isa pointer (a load at offset 0), which tier 2 refuses."""
    return build_stub_image(callers=((ldr(0, 1, 0), *WITNESS_TAIL),))[0]


def mixed():
    """One admitted value witness site and one refused closure site in separate callers."""
    return build_stub_image(callers=((('bl', ('stub', 0)), *WITNESS_TAIL), (ldr(8, 20, 16), blr(8), ret())),
                            imports=(Import(IMPORTED_ACCESSOR, 1),))[0]


IMAGES = dict(imported=lambda: imported_metadata(IMPORTED_ACCESSOR), runtime=lambda: imported_metadata(RUNTIME_METADATA),
              not_accessor=lambda: imported_metadata(OTHER_FUNCTION), local=local_accessor,
              unnamed=local_unnamed_callee, closure=closure_context, isa=isa_load, mixed=mixed)
