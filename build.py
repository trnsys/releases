#!/usr/bin/env python3
"""build.py — Local bundle assembly for TRNSYS releases.

Mirrors what .github/workflows/release.yml does in CI, with one difference:
runtime-cstb and runtime-transsolar are read from local paths (../runtime-cstb
and ../runtime-transsolar) rather than downloaded from GitHub, since those
repos may not yet be pushed/tagged.

Prerequisites:
  - gh CLI authenticated with access to the trnsys org
  - Local runtime repos at ../runtime-cstb and ../runtime-transsolar
  - Python 3.11+ (uses tomllib)

Usage:
    python build.py

Output:
    trnsys-macos-arm64.zip
    trnsys-windows.zip
    SHA256SUMS.txt

At the end, the script prints the `gh release create` command to run manually.
"""

import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
RUNTIME_CSTB = SCRIPT_DIR / ".." / "runtime-cstb"
RUNTIME_TRANSSOLAR = SCRIPT_DIR / ".." / "runtime-transsolar"


def main():
    # ── sanity checks ──────────────────────────────────────────────────────────

    if not RUNTIME_CSTB.is_dir():
        die(f"ERROR: runtime-cstb not found at {RUNTIME_CSTB}")
    if not RUNTIME_TRANSSOLAR.is_dir():
        die(f"ERROR: runtime-transsolar not found at {RUNTIME_TRANSSOLAR}")

    # ── parse manifest ─────────────────────────────────────────────────────────

    with open(SCRIPT_DIR / "manifest.toml", "rb") as f:
        manifest = tomllib.load(f)

    version = manifest["release"]["version"]
    c = manifest["components"]

    kernel_tag             = c["kernel"]
    engine_tag             = c["engine"]
    standard_types_tag     = c["standard-types"]
    solar_calcs_tag        = c["solar-calcs"]
    fluid_properties_tag   = c["fluid-properties"]
    trnexe_tag             = c["trnexe"]
    runtime_cstb_tag       = c["runtime-cstb"]
    runtime_transsolar_tag = c["runtime-transsolar"]

    print(f"==> Release version: {version}")
    print(f"    kernel              {kernel_tag}")
    print(f"    engine              {engine_tag}")
    print(f"    standard-types      {standard_types_tag}")
    print(f"    solar-calcs         {solar_calcs_tag}")
    print(f"    fluid-properties    {fluid_properties_tag}")
    print(f"    trnexe              {trnexe_tag}")
    print(f"    runtime-cstb        {runtime_cstb_tag}  (local)")
    print(f"    runtime-transsolar  {runtime_transsolar_tag}  (local)")
    print()

    # ── download core component artifacts ─────────────────────────────────────

    print("==> Downloading core component artifacts from GitHub...")
    dl = SCRIPT_DIR / "dl"
    dl.mkdir(exist_ok=True)

    downloads = [
        # macOS arm64
        (kernel_tag,           "trnsys/kernel",           "kernel-macos-arm64-runtime.tar.gz"),
        (kernel_tag,           "trnsys/kernel",           "kernel-resources.tar.gz"),
        (engine_tag,           "trnsys/engine",           "engine-macos-arm64-runtime.tar.gz"),
        (standard_types_tag,   "trnsys/standard-types",   "standard-types-macos-arm64-runtime.tar.gz"),
        (solar_calcs_tag,      "trnsys/solar-calcs",      "solar_calcs-macos-runtime.tar.gz"),
        (fluid_properties_tag, "trnsys/fluid-properties", "fluid-properties-macos-arm64-runtime.tar.gz"),
        (trnexe_tag,           "trnsys/trnexe",           "trnexe-macos-arm64-runtime.tar.gz"),
        # Windows
        (kernel_tag,           "trnsys/kernel",           "kernel-windows-runtime.zip"),
        (engine_tag,           "trnsys/engine",           "engine-windows-runtime.zip"),
        (standard_types_tag,   "trnsys/standard-types",   "standard-types-windows-runtime.zip"),
        (solar_calcs_tag,      "trnsys/solar-calcs",      "solar_calcs-windows-runtime.zip"),
        (fluid_properties_tag, "trnsys/fluid-properties", "fluid-properties-windows-x64-runtime.zip"),
        (trnexe_tag,           "trnsys/trnexe",           "trnexe-windows-runtime.zip"),
    ]

    for tag, repo, pattern in downloads:
        run(["gh", "release", "download", tag,
             "--repo", repo, "--pattern", pattern, "--clobber"], cwd=dl)

    # ── assemble macOS arm64 bundle ────────────────────────────────────────────
    # bin/ and resources/ only — no vendor runtime content on macOS.

    print("==> Assembling macOS arm64 bundle...")
    bundle_macos = SCRIPT_DIR / "bundle-macos"
    if bundle_macos.exists():
        shutil.rmtree(bundle_macos)
    (bundle_macos / "bin").mkdir(parents=True)
    (bundle_macos / "resources").mkdir(parents=True)

    for name in [
        "kernel-macos-arm64-runtime.tar.gz",
        "engine-macos-arm64-runtime.tar.gz",
        "standard-types-macos-arm64-runtime.tar.gz",
        "solar_calcs-macos-runtime.tar.gz",
        "fluid-properties-macos-arm64-runtime.tar.gz",
        "trnexe-macos-arm64-runtime.tar.gz",
    ]:
        with tarfile.open(dl / name, "r:gz") as tf:
            tf.extractall(bundle_macos / "bin")

    with tarfile.open(dl / "kernel-resources.tar.gz", "r:gz") as tf:
        tf.extractall(bundle_macos / "resources")

    print("    macOS bundle contents:")
    for p in sorted(bundle_macos.rglob("*")):
        if p.is_file():
            print(f"      {p.relative_to(bundle_macos)}")

    # ── assemble Windows bundle ────────────────────────────────────────────────
    # Exe/, Resources/ — core components
    # Studio/          ← runtime-cstb/studio/
    # Building/        ← runtime-transsolar/building/
    # UserLib/         ← runtime-cstb/type/ + runtime-transsolar/type/ (merged)

    print("==> Assembling Windows bundle...")
    bundle_windows = SCRIPT_DIR / "bundle-windows"
    if bundle_windows.exists():
        shutil.rmtree(bundle_windows)
    (bundle_windows / "Exe").mkdir(parents=True)
    (bundle_windows / "Resources").mkdir(parents=True)

    for name in [
        "kernel-windows-runtime.zip",
        "engine-windows-runtime.zip",
        "standard-types-windows-runtime.zip",
        "solar_calcs-windows-runtime.zip",
        "fluid-properties-windows-x64-runtime.zip",
        "trnexe-windows-runtime.zip",
    ]:
        with zipfile.ZipFile(dl / name) as zf:
            zf.extractall(bundle_windows / "Exe")

    with tarfile.open(dl / "kernel-resources.tar.gz", "r:gz") as tf:
        tf.extractall(bundle_windows / "Resources")

    shutil.copytree(RUNTIME_CSTB / "studio",        bundle_windows / "Studio")
    shutil.copytree(RUNTIME_TRANSSOLAR / "building", bundle_windows / "Building")

    userlib = bundle_windows / "UserLib"
    userlib.mkdir()
    shutil.copytree(RUNTIME_TRANSSOLAR / "type", userlib, dirs_exist_ok=True)

    print("    Windows bundle contents:")
    for p in sorted(bundle_windows.rglob("*")):
        if p.is_file():
            print(f"      {p.relative_to(bundle_windows)}")

    # ── package ────────────────────────────────────────────────────────────────

    print("==> Packaging...")

    macos_zip = SCRIPT_DIR / "trnsys-macos-arm64.zip"
    with zipfile.ZipFile(macos_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(bundle_macos.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(bundle_macos))

    windows_zip = SCRIPT_DIR / "trnsys-windows.zip"
    with zipfile.ZipFile(windows_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(bundle_windows.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(bundle_windows))

    print("    Packages:")
    for p in sorted(SCRIPT_DIR.glob("trnsys-*.zip")):
        print(f"      {p.stat().st_size / 1024 / 1024:.1f}M  {p.name}")

    # ── checksums ──────────────────────────────────────────────────────────────

    print("==> Generating checksums...")
    zips = sorted(SCRIPT_DIR.glob("trnsys-*.zip"))
    cmd = "sha256sum" if shutil.which("sha256sum") else "shasum"
    args = [cmd] + (["-a", "256"] if cmd == "shasum" else []) + [str(p) for p in zips]
    result = subprocess.run(args, check=True, capture_output=True, text=True)
    checksums = result.stdout
    (SCRIPT_DIR / "SHA256SUMS.txt").write_text(checksums)
    for line in checksums.splitlines():
        print(f"      {line}")

    # ── instructions ───────────────────────────────────────────────────────────

    tag = f"v{version}"
    print()
    print("==> Done. To publish:")
    print()
    print(f"    cd {SCRIPT_DIR}")
    print(f"    git tag {tag} && git push origin {tag}")
    print()
    print(f"    gh release create {tag} \\")
    print(f"      --repo trnsys/releases \\")
    print(f'      --title "TRNSYS {version}" \\')
    print(f"      --generate-notes \\")
    print(f"      trnsys-macos-arm64.zip \\")
    print(f"      trnsys-windows.zip \\")
    print(f"      SHA256SUMS.txt")
    print()


# -- Helpers ----------------------------------------------------------------


def run(args, **kwargs):
    try:
        subprocess.run([str(a) for a in args], check=True, **kwargs)
    except subprocess.CalledProcessError:
        die(f"Command failed: {' '.join(str(a) for a in args)}")


def die(message):
    print(message, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
