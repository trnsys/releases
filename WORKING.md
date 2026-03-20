# Working: Build all Windows x64 artifacts and assemble release bundle

Read this file completely before doing anything. Everything you need is here.

---

## Goal

Build every TRNSYS component for Windows x64, upload correctly-named artifacts to each component repo's GitHub release, then assemble and publish the final release bundle.

When done, `trnsys/releases` has a tagged release with `trnsys-windows-x64.zip` containing everything needed for a Windows installation.

## What's already done (macOS side)

Before you start, the macOS artifacts have been renamed. The only macOS artifact that was inconsistent was `solar_calcs-macos-runtime.tar.gz` on solar-calcs v0.1.0 — it's now `solar-calcs-macos-arm64-runtime.tar.gz`. All other macOS artifacts already had correct names.

You only need to handle Windows.

## Artifact naming convention

All artifacts follow this pattern:

```
{repo}-{os}-{arch}-{variant}.zip
```

- `{repo}` — repo name with hyphens (matching GitHub repo name)
- `{os}` — `windows`
- `{arch}` — `x64`
- `{variant}` — `runtime` or `dev`

## Prerequisites

Before starting, verify each of these:

```powershell
python --version          # 3.11+
rustc --version           # stable
cargo --version
node --version            # 20+
ifort /help               # Intel Fortran classic — run from oneAPI command prompt
gh auth status            # authenticated with trnsys org access
```

If `ifort` is not on PATH, open an "Intel oneAPI command prompt" or run:
```cmd
"C:\Program Files (x86)\Intel\oneAPI\setvars.bat"
```

All repos should be cloned under the same parent directory (e.g. `C:\repos\trnsys\`).
The script assumes sibling repos can be found at `..\{repo-name}\`.

---

## Build order

Components must be built in this order due to dependencies:

```
1. solar-calcs           (no deps)
2. fluid-properties      (no deps)
3. trnsys-license        (no deps — Rust crate inside trn repo)
4. kernel                (deps: solar-calcs dev, fluid-properties dev)
5. engine                (deps: kernel dev, trnsys-license)
6. standard-types        (deps: kernel dev)
7. trnexe                (no Fortran deps — Rust/Tauri)
```

---

## Step 1: solar-calcs

```cmd
cd ..\solar-calcs
ifort /nologo /Qsave /Qzero /fpconstant /libs:dll /threads /dll /Fe:solar_calcs.dll src\FprimeCalculations.f90
```

Verify:
```powershell
Get-Item solar_calcs.dll | Select-Object Name, Length
Get-Item solar_calcs.lib | Select-Object Name, Length
```

Package:
```powershell
Compress-Archive -Path solar_calcs.dll -DestinationPath solar-calcs-windows-x64-runtime.zip -Force
Compress-Archive -Path solar_calcs.lib -DestinationPath solar-calcs-windows-x64-dev.zip -Force
```

Upload (replace old artifacts on existing release):
```powershell
gh release delete-asset v0.1.0 solar_calcs-windows-runtime.zip --repo trnsys/solar-calcs --yes
gh release delete-asset v0.1.0 solar_calcs-windows-dev.zip --repo trnsys/solar-calcs --yes
gh release upload v0.1.0 solar-calcs-windows-x64-runtime.zip --repo trnsys/solar-calcs
gh release upload v0.1.0 solar-calcs-windows-x64-dev.zip --repo trnsys/solar-calcs
```

Verify:
```powershell
gh release view v0.1.0 --repo trnsys/solar-calcs --json assets -q ".assets[].name"
```

Expected: `solar-calcs-windows-x64-runtime.zip`, `solar-calcs-windows-x64-dev.zip`, plus existing macOS artifacts.

Clean up build artifacts before moving on:
```powershell
Remove-Item solar_calcs.dll, solar_calcs.lib, solar_calcs.obj, *.mod -ErrorAction SilentlyContinue
Remove-Item solar-calcs-windows-x64-runtime.zip, solar-calcs-windows-x64-dev.zip -ErrorAction SilentlyContinue
```

---

## Step 2: fluid-properties

```cmd
cd ..\fluid-properties
set FC=ifort
python build.py windows-x64 release
```

Verify:
```powershell
Get-Item build\nist_steam.dll | Select-Object Name, Length
Get-Item build\CoolProp.dll | Select-Object Name, Length
```

Package:
```powershell
Compress-Archive -Path build\nist_steam.dll, build\CoolProp.dll -DestinationPath fluid-properties-windows-x64-runtime.zip -Force
Compress-Archive -Path build\nist_steam.lib, build\CoolProp.lib, build\*.mod -DestinationPath fluid-properties-windows-x64-dev.zip -Force
```

Upload (names already correct — just verify they exist):
```powershell
gh release view v0.1.0 --repo trnsys/fluid-properties --json assets -q ".assets[].name"
```

If the existing artifacts have the correct names (`fluid-properties-windows-x64-runtime.zip`, `fluid-properties-windows-x64-dev.zip`), skip the upload. If they need replacing:
```powershell
gh release delete-asset v0.1.0 fluid-properties-windows-x64-runtime.zip --repo trnsys/fluid-properties --yes
gh release delete-asset v0.1.0 fluid-properties-windows-x64-dev.zip --repo trnsys/fluid-properties --yes
gh release upload v0.1.0 fluid-properties-windows-x64-runtime.zip --repo trnsys/fluid-properties
gh release upload v0.1.0 fluid-properties-windows-x64-dev.zip --repo trnsys/fluid-properties
```

Clean up:
```powershell
Remove-Item -Recurse build -ErrorAction SilentlyContinue
Remove-Item fluid-properties-windows-x64-runtime.zip, fluid-properties-windows-x64-dev.zip -ErrorAction SilentlyContinue
```

---

## Step 3: trnsys-license

This is a Rust crate inside the `trn` repo. The engine links against the static lib at build time.

```cmd
cd ..\trn
cargo build --release -p trnsys-license
```

Verify:
```powershell
Get-Item target\release\trnsys_license.lib | Select-Object Name, Length
Get-Item crates\trnsys-license\include\trnsys_license.h | Select-Object Name, Length
```

Package and upload to the `trn` repo release (engine CI downloads from here):
```powershell
Compress-Archive -Path target\release\trnsys_license.lib, crates\trnsys-license\include\trnsys_license.h -DestinationPath trnsys-license-windows-x64.zip -Force
gh release upload v0.7.0 trnsys-license-windows-x64.zip --repo trnsys/trn
```

Verify:
```powershell
gh release view v0.7.0 --repo trnsys/trn --json assets -q ".assets[].name"
```

Expected: `trnsys-license-macos-arm64.tar.gz` (already uploaded) and `trnsys-license-windows-x64.zip`.

The `.lib` file is also needed locally by the engine build in step 5.

Clean up:
```powershell
Remove-Item trnsys-license-windows-x64.zip -ErrorAction SilentlyContinue
```

---

## Step 4: kernel

Set up dependencies:
```powershell
cd ..\kernel
New-Item -ItemType Directory -Path deps\solar_calcs -Force
New-Item -ItemType Directory -Path deps\fluid_properties -Force

gh release download v0.1.0 --repo trnsys/solar-calcs --pattern "solar-calcs-windows-x64-dev.zip" --dir deps
Expand-Archive deps\solar-calcs-windows-x64-dev.zip -DestinationPath deps\solar_calcs -Force

gh release download v0.1.0 --repo trnsys/fluid-properties --pattern "fluid-properties-windows-x64-dev.zip" --dir deps
Expand-Archive deps\fluid-properties-windows-x64-dev.zip -DestinationPath deps\fluid_properties -Force
```

Build:
```cmd
set FC=ifort
python build.py windows release
```

Build TRNDll64.dll (legacy adapter):
```cmd
ifort /nologo /libs:dll /threads /dll /Fe:build\TRNDll64.dll /I:build legacy\TRNDll.f90 build\kernel.lib
```

Verify:
```powershell
foreach ($f in @("build\kernel.dll", "build\kernel.lib", "build\TRNDll64.dll")) {
    Get-Item $f | Select-Object Name, Length
}
```

Package:
```powershell
Compress-Archive -Path build\kernel.dll, build\TRNDll64.dll -DestinationPath kernel-windows-x64-runtime.zip -Force
Compress-Archive -Path build\kernel.lib, build\*.mod -DestinationPath kernel-windows-x64-dev.zip -Force
```

Upload:
```powershell
gh release delete-asset v0.2.1 kernel-windows-runtime.zip --repo trnsys/kernel --yes
gh release delete-asset v0.2.1 kernel-windows-dev.zip --repo trnsys/kernel --yes
gh release upload v0.2.1 kernel-windows-x64-runtime.zip --repo trnsys/kernel
gh release upload v0.2.1 kernel-windows-x64-dev.zip --repo trnsys/kernel
```

Verify:
```powershell
gh release view v0.2.1 --repo trnsys/kernel --json assets -q ".assets[].name"
```

Clean up:
```powershell
Remove-Item -Recurse deps, build -ErrorAction SilentlyContinue
Remove-Item kernel-windows-x64-runtime.zip, kernel-windows-x64-dev.zip -ErrorAction SilentlyContinue
```

---

## Step 5: engine

Set up dependencies:
```powershell
cd ..\engine
New-Item -ItemType Directory -Path deps\kernel -Force
New-Item -ItemType Directory -Path deps\licensing -Force

gh release download v0.2.1 --repo trnsys/kernel --pattern "kernel-windows-x64-dev.zip" --dir deps
Expand-Archive deps\kernel-windows-x64-dev.zip -DestinationPath deps\kernel -Force

Copy-Item ..\trn\target\release\trnsys_license.lib deps\licensing\
```

Build:
```cmd
set FC=ifort
python build.py windows release
```

Verify:
```powershell
Get-Item build\engine.dll | Select-Object Name, Length
Get-Item build\engine.lib | Select-Object Name, Length
```

Package:
```powershell
Compress-Archive -Path build\engine.dll -DestinationPath engine-windows-x64-runtime.zip -Force
Compress-Archive -Path build\engine.lib, build\*.mod -DestinationPath engine-windows-x64-dev.zip -Force
```

Upload:
```powershell
gh release delete-asset v0.2.1 engine-windows-runtime.zip --repo trnsys/engine --yes
gh release delete-asset v0.2.1 engine-windows-dev.zip --repo trnsys/engine --yes
gh release upload v0.2.1 engine-windows-x64-runtime.zip --repo trnsys/engine
gh release upload v0.2.1 engine-windows-x64-dev.zip --repo trnsys/engine
```

Verify:
```powershell
gh release view v0.2.1 --repo trnsys/engine --json assets -q ".assets[].name"
```

Clean up:
```powershell
Remove-Item -Recurse deps, build -ErrorAction SilentlyContinue
Remove-Item engine-windows-x64-runtime.zip, engine-windows-x64-dev.zip -ErrorAction SilentlyContinue
```

---

## Step 6: standard-types

Set up dependencies:
```powershell
cd ..\standard-types
New-Item -ItemType Directory -Path deps\kernel -Force

gh release download v0.2.1 --repo trnsys/kernel --pattern "kernel-windows-x64-dev.zip" --dir deps
Expand-Archive deps\kernel-windows-x64-dev.zip -DestinationPath deps\kernel -Force
```

Build:
```cmd
set FC=ifort
python build.py windows release
```

Verify:
```powershell
Get-Item build\types.dll | Select-Object Name, Length
```

Package:
```powershell
Compress-Archive -Path build\types.dll -DestinationPath standard-types-windows-x64-runtime.zip -Force
```

Upload:
```powershell
gh release delete-asset v0.1.0 standard-types-windows-runtime.zip --repo trnsys/standard-types --yes
gh release upload v0.1.0 standard-types-windows-x64-runtime.zip --repo trnsys/standard-types
```

Verify:
```powershell
gh release view v0.1.0 --repo trnsys/standard-types --json assets -q ".assets[].name"
```

Clean up:
```powershell
Remove-Item -Recurse deps, build -ErrorAction SilentlyContinue
Remove-Item standard-types-windows-x64-runtime.zip -ErrorAction SilentlyContinue
```

---

## Step 7: trnexe

```powershell
cd ..\trnexe
npm ci
npx tauri build
```

Verify:
```powershell
Get-Item src-tauri\target\release\trnexe.exe | Select-Object Name, Length
```

Package:
```powershell
Compress-Archive -Path src-tauri\target\release\trnexe.exe -DestinationPath trnexe-windows-x64-runtime.zip -Force
```

Upload:
```powershell
gh release delete-asset v0.2.0 trnexe-windows-runtime.zip --repo trnsys/trnexe --yes
gh release upload v0.2.0 trnexe-windows-x64-runtime.zip --repo trnsys/trnexe
```

Verify:
```powershell
gh release view v0.2.0 --repo trnsys/trnexe --json assets -q ".assets[].name"
```

Clean up:
```powershell
Remove-Item trnexe-windows-x64-runtime.zip -ErrorAction SilentlyContinue
```

---

## Step 8: Build trn for Windows

```powershell
cd ..\trn
git checkout main
git pull
cargo build --release
```

Verify:
```powershell
Get-Item target\release\trn.exe | Select-Object Name, Length
target\release\trn.exe --version
```

Upload to `trn-releases` v0.7.0 (the release will have been created from macOS already):
```powershell
Compress-Archive -Path target\release\trn.exe -DestinationPath trn-v0.7.0-x86_64-pc-windows-msvc.zip -Force
gh release upload v0.7.0 trn-v0.7.0-x86_64-pc-windows-msvc.zip --repo trnsys/trn-releases
```

Verify:
```powershell
gh release view v0.7.0 --repo trnsys/trn-releases --json assets -q ".assets[].name"
```

Expected: `trn-v0.7.0-aarch64-apple-darwin.tar.gz` and `trn-v0.7.0-x86_64-pc-windows-msvc.zip`.

Clean up:
```powershell
Remove-Item trn-v0.7.0-x86_64-pc-windows-msvc.zip -ErrorAction SilentlyContinue
```

---

## Step 9: Assemble release bundle

Return to the releases repo:

```powershell
cd ..\releases
git checkout build-windows-x64
git pull
python build.py
```

This downloads all artifacts (using the new names in build.py), assembles both the macOS and Windows bundles, and produces `trnsys-macos-arm64.zip` and `trnsys-windows-x64.zip`.

Verify the Windows bundle contents:
```powershell
# Should list: Exe/, Resources/, Building/, Studio/, UserLib/
# Exe/ should have: engine.dll, kernel.dll, types.dll, nist_steam.dll, solar_calcs.dll,
#                   CoolProp.dll, TRNDll64.dll, trnexe.exe, plus Intel Fortran runtime DLLs
```

Follow the instructions printed by build.py to tag and publish. The tag and `gh release create` command will be printed at the end.

---

## If something fails

- **ifort not found**: Run from an Intel oneAPI command prompt, or source `setvars.bat`.
- **gh permission denied**: Check `gh auth status` and ensure trnsys org access.
- **build.py fails on deps**: The previous step's upload may not have completed. Verify with `gh release view`.
- **Link errors in engine**: The trnsys-license static lib must be built first (step 3).

## Principles

- **Follow the order.** Dependencies are strict — don't skip ahead.
- **Verify after every step.** Check file sizes and release assets before moving on.
- **Don't modify source files.** This is a build-and-upload task.
- **Clean up after each step.** Don't let artifacts from one step contaminate the next.
