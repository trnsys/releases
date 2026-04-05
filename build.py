#!/usr/bin/env python3
"""build.py — Local bundle assembly for TRNSYS releases.

This script delegates to the shared trnsys_bundle module in build-tools.
It ensures that the local build-tools repo is in the PYTHONPATH.

Usage:
    python build.py [macos|windows|linux]

If no platform is specified, it builds macos, windows, and linux.
"""

import sys
import os
from pathlib import Path

# Ensure build-tools is in PYTHONPATH so we can import trnsys_bundle
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BUILD_TOOLS = REPO_ROOT / "build-tools"

if not BUILD_TOOLS.is_dir():
    print(f"ERROR: build-tools not found at {BUILD_TOOLS}")
    sys.exit(1)

sys.path.append(str(BUILD_TOOLS))

try:
    import trnsys_bundle
    from bundle_plan import load_manifest
except ImportError as e:
    print(f"ERROR: failed to import trnsys_bundle or bundle_plan: {e}")
    sys.exit(1)

def main():
    # If no platforms are specified, default to all platforms in the manifest
    if len(sys.argv) > 1:
        platforms = sys.argv[1:]
    else:
        try:
            manifest = load_manifest(SCRIPT_DIR / "manifest.toml")
            platforms = list(manifest["platforms"].keys())
        except Exception as e:
            print(f"ERROR: failed to load manifest to determine default platforms: {e}")
            sys.exit(1)
    
    print(f"==> Target platforms: {', '.join(platforms)}")

    for platform in platforms:
        print(f"\n==> Assembling {platform}...")
        try:
            # We bypass the CLI parser and call the command directly to avoid
            # nested argparse confusion.
            trnsys_bundle.cmd_assemble(
                platform=platform,
                manifest_path=SCRIPT_DIR / "manifest.toml",
                repo_root=SCRIPT_DIR
            )
        except Exception as e:
            print(f"ERROR: assembly failed for {platform}: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
