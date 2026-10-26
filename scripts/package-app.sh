#!/bin/bash
# Assemble a local developer app with a prepared private CPython runtime by default.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="$PROJECT_DIR/dist"
CONFIGURATION="debug"
AD_HOC_SIGN=0
PRIVATE_PYTHON="$PROJECT_DIR/build/private-python-3.15.0"
EXTERNAL_PYTHON=0
SOURCE_COMMIT=""
ACCEPTED_VENDOR_SOURCE=""
NATIVE_BUILD_RECEIPT=""
BUNDLE_VERSION="0.3.3"
BUNDLE_BUILD="12"

usage() {
    cat <<'USAGE'
Usage: scripts/package-app.sh [--output-dir DIRECTORY] [--debug|--release] [--ad-hoc-sign] [--python-runtime DIRECTORY|--external-python] [--version VERSION --build NUMBER --source-commit COMMIT] [--accepted-vendor-source COMMIT] [--native-build-receipt FILE]

Build and package AIRS.app for local use on macOS 14 or newer.
Includes the native airs-entitlements command at Contents/MacOS/airs-entitlements.
The app includes owned engine source and the prepared private Python 3.15.0 runtime.
--python-runtime selects a prepared runtime directory with its reusable receipt.
--external-python deliberately creates a source-only developer package instead.
Debug is the default for a quick first build; --release opts into optimization.
--ad-hoc-sign signs only the newly assembled local app with codesign -s -.
No distribution identity, notarization, upload, or release publication is used.
An existing AIRS.app at the destination is left untouched and is an error.
USAGE
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --output-dir)
            if [ "$#" -lt 2 ]; then
                printf '%s\n' 'Missing directory after --output-dir.' >&2
                exit 2
            fi
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --python-runtime)
            if [ "$#" -lt 2 ]; then printf '%s\n' 'Missing directory after --python-runtime.' >&2; exit 2; fi
            PRIVATE_PYTHON="$2"; shift 2 ;;
        --version|--build|--source-commit|--accepted-vendor-source|--native-build-receipt)
            if [ "$#" -lt 2 ]; then printf 'Missing value for %s\n' "$1" >&2; exit 2; fi
            case "$1" in
                --version) BUNDLE_VERSION="$2" ;;
                --build) BUNDLE_BUILD="$2" ;;
                --source-commit) SOURCE_COMMIT="$2" ;;
                --accepted-vendor-source) ACCEPTED_VENDOR_SOURCE="$2" ;;
                --native-build-receipt) NATIVE_BUILD_RECEIPT="$2" ;;
            esac
            shift 2 ;;
        --external-python) EXTERNAL_PYTHON=1; shift ;;
        --debug) CONFIGURATION="debug"; shift ;;
        --release) CONFIGURATION="release"; shift ;;
        --ad-hoc-sign) AD_HOC_SIGN=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
    esac
done

python3 -B - "$BUNDLE_VERSION" "$BUNDLE_BUILD" "$SOURCE_COMMIT" <<'PYIDENTITY'
import re, sys
version, build, commit = sys.argv[1:]
if (re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version) is None
        or re.fullmatch(r'[1-9][0-9]{0,9}', build) is None
        or (commit and re.fullmatch(r'[0-9a-f]{40}', commit) is None)):
    raise SystemExit('Invalid version, build or exact source commit')
PYIDENTITY

if [ "$(uname -s)" != "Darwin" ]; then
    printf '%s\n' 'Packaging requires macOS 14+ and the Apple Swift toolchain.' >&2
    exit 2
fi
if ! command -v swift >/dev/null 2>&1; then
    printf '%s\n' 'Swift was not found. Install Xcode or its command-line tools.' >&2
    exit 2
fi
if [ ! -f "$PROJECT_DIR/airs_cli.py" ] || [ ! -d "$PROJECT_DIR/src/airs" ]; then
    printf '%s\n' 'Expected the owned engine bootstrap and src/airs beside scripts/.' >&2
    exit 2
fi

case "$OUTPUT_DIR" in
    /*) ;;
    *) OUTPUT_DIR="$PWD/$OUTPUT_DIR" ;;
esac
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
APP_PATH="$OUTPUT_DIR/AIRS.app"
if [ -e "$APP_PATH" ] || [ -L "$APP_PATH" ]; then
    printf 'Destination already exists: %s\nChoose another --output-dir or move the existing app first.\n' "$APP_PATH" >&2
    exit 2
fi

if [ "$EXTERNAL_PYTHON" -eq 0 ]; then
    # Metadata-bound reuse of the sealed preparation, not repeated dependency,
    # signature or runtime verification. No network or system installation here.
    python3 -I -B "$SCRIPT_DIR/prepare-private-python.py" --output-dir "$PRIVATE_PYTHON" --reuse-only
fi

# Release executables must not embed this machine's checkout or build paths.
BUILD_FLAGS=(--configuration "$CONFIGURATION" --jobs 2)
if [ "$CONFIGURATION" = "release" ]; then
    if [ -n "$ACCEPTED_VENDOR_SOURCE" ]; then
        # Caller supplies a retained accepted source identity. Compare immutable
        # Git tree identity only; never rescan unchanged vendor content.
        python3 -B - "$PROJECT_DIR" "$ACCEPTED_VENDOR_SOURCE" <<'PYVENDOR'
import re, subprocess, sys
root, accepted = sys.argv[1:]
if re.fullmatch(r'[0-9a-f]{40}', accepted) is None:
    raise SystemExit('Expected an exact accepted vendor-source commit')
def git(*args):
    return subprocess.check_output(['git', '-C', root, *args], text=True).strip()
if git('rev-parse', accepted + ':native/Vendor/Lumen') != git('rev-parse', 'HEAD:native/Vendor/Lumen'):
    raise SystemExit('Vendor source differs from accepted identity')
if git('status', '--porcelain', '--untracked-files=all', '--', 'native/Vendor/Lumen'):
    raise SystemExit('Vendor working tree differs from accepted identity')
if git('ls-files', '--others', '--ignored', '--exclude-standard', '--',
       'native/Vendor/Lumen/Sources', 'native/Vendor/Lumen/Package.swift'):
    raise SystemExit('Ignored vendor compiler/resource inputs are not covered by the accepted identity')
print('Reused accepted immutable Lumen source identity; no source scan repeated.')
PYVENDOR
    else
        python3 -I -B "$SCRIPT_DIR/check-release-content.py" --lumen-source "$PROJECT_DIR/native/Vendor/Lumen"
    fi
    BUILD_FLAGS+=(-Xswiftc -debug-prefix-map -Xswiftc "$PROJECT_DIR=/AIRS"
                 -Xswiftc -file-prefix-map -Xswiftc "$PROJECT_DIR=/AIRS")
fi
if [ -n "$NATIVE_BUILD_RECEIPT" ]; then
    BUILD_DIR="$(python3 -B "$SCRIPT_DIR/reuse_native_build.py" --source "$PROJECT_DIR" --receipt "$NATIVE_BUILD_RECEIPT")"
else
    swift build --package-path "$PROJECT_DIR/native" "${BUILD_FLAGS[@]}" --product AIRSApp
    swift build --package-path "$PROJECT_DIR/native" "${BUILD_FLAGS[@]}" --product airs-entitlements
    BUILD_DIR="$(swift build --package-path "$PROJECT_DIR/native" --configuration "$CONFIGURATION" --show-bin-path)"
fi
if [ ! -x "$BUILD_DIR/AIRSApp" ]; then
    printf '%s\n' 'Swift did not produce the expected AIRSApp executable.' >&2
    exit 3
fi
if [ ! -x "$BUILD_DIR/airs-entitlements" ]; then
    printf '%s\n' 'Swift did not produce the expected airs-entitlements executable.' >&2
    exit 3
fi

STAGING_DIR="$(mktemp -d "$OUTPUT_DIR/.airs-package.XXXXXX")"
cleanup() { rm -rf "$STAGING_DIR"; }
trap cleanup EXIT
STAGED_APP="$STAGING_DIR/AIRS.app"
CONTENTS="$STAGED_APP/Contents"
ENGINE_DIR="$CONTENTS/Resources/Engine"
mkdir -p "$CONTENTS/MacOS" "$ENGINE_DIR/src/airs"
cp "$BUILD_DIR/AIRSApp" "$CONTENTS/MacOS/AIRSApp"
chmod 755 "$CONTENTS/MacOS/AIRSApp"
cp "$BUILD_DIR/airs-entitlements" "$CONTENTS/MacOS/airs-entitlements"
chmod 755 "$CONTENTS/MacOS/airs-entitlements"
# Lumen's generated Bundle.module accessor resolves this from the app's Resources.
LUMEN_RESOURCES="$BUILD_DIR/Lumen_LumenUI.bundle"
if [ ! -d "$LUMEN_RESOURCES" ]; then
    printf 'Missing Lumen UI resource bundle: %s\n' "$LUMEN_RESOURCES" >&2
    exit 3
fi
/usr/bin/ditto "$LUMEN_RESOURCES" "$CONTENTS/Resources/Lumen_LumenUI.bundle"
cp "$PROJECT_DIR/airs_cli.py" "$ENGINE_DIR/airs_cli.py"
cp "$PROJECT_DIR/LICENSE" "$CONTENTS/Resources/AIRS-LICENSE.txt"
cp "$PROJECT_DIR/THIRD_PARTY_NOTICES.md" "$CONTENTS/Resources/THIRD_PARTY_NOTICES.md"
mkdir -p "$CONTENTS/Resources/ThirdPartyNotices"
cp "$PROJECT_DIR/native/Vendor/Lumen/LICENSE" "$CONTENTS/Resources/ThirdPartyNotices/Lumen-LICENSE.txt"
cp "$PROJECT_DIR/native/Vendor/EntitlementDiff/LICENSE" "$CONTENTS/Resources/ThirdPartyNotices/EntitlementDiff-LICENSE.txt"
cp "$PROJECT_DIR/third_party/EntitlementLens/LICENSE" "$CONTENTS/Resources/ThirdPartyNotices/EntitlementLens-LICENSE.txt"
cp "$PROJECT_DIR/third_party/gimli/LICENSE-MIT" "$CONTENTS/Resources/ThirdPartyNotices/gimli-LICENSE-MIT.txt"
if [ "$EXTERNAL_PYTHON" -eq 0 ]; then
    mkdir -p "$CONTENTS/Frameworks" "$CONTENTS/Resources/RuntimeNotices"
    /usr/bin/ditto "$PRIVATE_PYTHON/Python.framework" "$CONTENTS/Frameworks/Python.framework"
    /usr/bin/ditto "$PRIVATE_PYTHON/Notices" "$CONTENTS/Resources/RuntimeNotices"
    # The application does not use CPython's deliberately malformed test archives.
    # Trim only this fresh bundle copy; preserve the prepared runtime and receipt.
    rm -rf "$CONTENTS/Frameworks/Python.framework/Versions/3.15/lib/python3.15/test" \
        "$CONTENTS/Frameworks/Python.framework/Versions/3.15/lib/python3.15/ensurepip"
    # Keep machine-specific verification metadata local. This is informational
    # provenance only; the sealed receipt above remains the reuse authority.
    python3 -I -B - "$PRIVATE_PYTHON/runtime-receipt.json" "$CONTENTS/Resources/RuntimeNotices/runtime-info.json" <<'PYINFO'
import json, sys
from pathlib import Path
receipt = json.loads(Path(sys.argv[1]).read_text())
keys = ("python_version", "source_url", "source_sha256", "omitted", "scope")
info = {k: receipt[k] for k in keys}
info["packaged_omissions"] = ["lib/python3.15/test", "lib/python3.15/ensurepip"]
Path(sys.argv[2]).write_text(json.dumps(info, indent=2) + "\n")
PYINFO
    cp "$PRIVATE_PYTHON/Python.framework/Versions/3.15/lib/python3.15/LICENSE.txt" "$CONTENTS/Resources/RuntimeNotices/Python-LICENSE.txt"
fi

# App icon: compile the Icon Composer bundle into Assets.car + AIRS.icns.
ICON_SOURCE="$PROJECT_DIR/resources/AIRS.icon"
if [ ! -d "$ICON_SOURCE" ]; then
    printf 'Missing app icon: %s\n' "$ICON_SOURCE" >&2
    exit 3
fi
xcrun actool "$ICON_SOURCE" --compile "$CONTENTS/Resources" --platform macosx \
    --minimum-deployment-target 14.0 --app-icon AIRS \
    --output-partial-info-plist "$STAGING_DIR/icon-partial.plist" >/dev/null

# Copy only owned Python source, retaining subpackages. Exclude caches/test inputs.
while IFS= read -r -d '' SOURCE_FILE; do
    RELATIVE_PATH="${SOURCE_FILE#"$PROJECT_DIR/src/airs/"}"
    DESTINATION="$ENGINE_DIR/src/airs/$RELATIVE_PATH"
    mkdir -p "$(dirname "$DESTINATION")"
    cp "$SOURCE_FILE" "$DESTINATION"
done < <(find "$PROJECT_DIR/src/airs" -type f -name '*.py' -print0)

cat > "$CONTENTS/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key><string>en</string>
    <key>CFBundleDisplayName</key><string>AIRS</string>
    <key>CFBundleExecutable</key><string>AIRSApp</string>
    <key>CFBundleIconFile</key><string>AIRS</string>
    <key>CFBundleIconName</key><string>AIRS</string>
    <key>CFBundleIdentifier</key><string>dev.airs.app</string>
    <key>CFBundleInfoDictionaryVersion</key><string>6.0</string>
    <key>CFBundleName</key><string>AIRS</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>0.3.3</string>
    <key>CFBundleVersion</key><string>12</string>
    <key>LSMinimumSystemVersion</key><string>14.0</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>CFBundleDocumentTypes</key>
    <array><dict>
        <key>CFBundleTypeName</key><string>AIRS and Entitlement Comparison Reports</string>
        <key>CFBundleTypeRole</key><string>Viewer</string>
        <key>LSHandlerRank</key><string>Alternate</string>
        <key>LSItemContentTypes</key><array><string>public.json</string><string>dev.airs.inspection</string><string>dev.airs.review</string></array>
    </dict></array>
    <key>UTExportedTypeDeclarations</key><array><dict>
        <key>UTTypeIdentifier</key><string>dev.airs.inspection</string>
        <key>UTTypeDescription</key><string>AIRS Inspection</string>
        <key>UTTypeConformsTo</key><array><string>public.json</string></array>
        <key>UTTypeTagSpecification</key><dict>
            <key>public.filename-extension</key><array><string>airsinspect</string></array>
        </dict>
    </dict><dict>
        <key>UTTypeIdentifier</key><string>dev.airs.review</string>
        <key>UTTypeDescription</key><string>AIRS Review Archive</string>
        <key>UTTypeConformsTo</key><array><string>public.json</string></array>
        <key>UTTypeTagSpecification</key><dict>
            <key>public.filename-extension</key><array><string>airsreview</string></array>
        </dict>
    </dict></array>
</dict>
</plist>
PLIST
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $BUNDLE_VERSION" "$CONTENTS/Info.plist"
/usr/libexec/PlistBuddy -c "Set :CFBundleVersion $BUNDLE_BUILD" "$CONTENTS/Info.plist"
if [ -n "$SOURCE_COMMIT" ]; then
    python3 -B "$SCRIPT_DIR/build_provenance.py" --source "$PROJECT_DIR" \
        --expected-commit "$SOURCE_COMMIT" --bundle-id dev.airs.app --build "$BUNDLE_BUILD" \
        --output "$CONTENTS/Resources/AIRSBuildProvenance.json"
fi
if [ "$EXTERNAL_PYTHON" -eq 0 ]; then
    /usr/libexec/PlistBuddy -c 'Add :AIRSPrivatePythonVersion string 3.15.0' "$CONTENTS/Info.plist"
fi
printf 'APPL????' > "$CONTENTS/PkgInfo"
/usr/bin/plutil -lint "$CONTENTS/Info.plist"

if [ "$CONFIGURATION" = "release" ]; then
    # The linker also emits object-file paths in its debug symbol table.
    # Strip only the newly copied owned executables; retain build symbols locally.
    /usr/bin/strip -S -x "$CONTENTS/MacOS/AIRSApp" "$CONTENTS/MacOS/airs-entitlements"
    python3 -I -B "$SCRIPT_DIR/check-release-content.py" "$STAGED_APP"
fi

if [ "$AD_HOC_SIGN" -eq 1 ]; then
    /usr/bin/codesign --force --sign - "$CONTENTS/MacOS/airs-entitlements"
    /usr/bin/codesign --force --sign - "$STAGED_APP"
    /usr/bin/codesign --verify --strict --verbose=2 "$STAGED_APP"
fi

# Recheck immediately before moving; do not deliberately replace an existing app.
if [ -e "$APP_PATH" ] || [ -L "$APP_PATH" ]; then
    printf 'Destination appeared during the build: %s\n' "$APP_PATH" >&2
    exit 2
fi
mv "$STAGED_APP" "$APP_PATH"
printf 'Created local developer app: %s\n' "$APP_PATH"
if [ "$EXTERNAL_PYTHON" -eq 0 ]; then
    printf '%s\n' 'Private Python 3.15.0 is included; no separate interpreter installation is required.'
else
    printf '%s\n' 'External-Python developer package: choose a Python 3.11+ executable in Settings.'
fi
