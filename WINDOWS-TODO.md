# Windows Build TODO — alpha.6

All macOS artifacts are uploaded. This doc covers everything needed on Windows.

## Prerequisites

```powershell
rustc --version    # stable
cargo --version
node --version     # 20+
gh auth status     # authenticated with trnsys org access
```

## Step 1: Build and upload trn v0.8.0

```powershell
cd path\to\trn
git checkout main
git pull

cargo build --release
target\release\trn.exe --version   # should say 0.8.0

Compress-Archive -Path target\release\trn.exe -DestinationPath trn-v0.8.0-x86_64-pc-windows-msvc.zip -Force
gh release upload v0.8.0 trn-v0.8.0-x86_64-pc-windows-msvc.zip --repo trnsys/trn-releases

# Verify
gh release view v0.8.0 --repo trnsys/trn-releases --json assets -q ".assets[].name"
# Expected: trn-v0.8.0-aarch64-apple-darwin.tar.gz and trn-v0.8.0-x86_64-pc-windows-msvc.zip

Remove-Item trn-v0.8.0-x86_64-pc-windows-msvc.zip
```

## Step 2: Build and upload trnsys-license for v0.8.0

The engine links against this at build time.

```powershell
cd path\to\trn
cargo build --release -p trnsys-license

Compress-Archive -Path target\release\trnsys_license.lib, crates\trnsys-license\include\trnsys_license.h -DestinationPath trnsys-license-windows-x64.zip -Force
gh release upload v0.8.0 trnsys-license-windows-x64.zip --repo trnsys/trn

# Verify
gh release view v0.8.0 --repo trnsys/trn --json assets -q ".assets[].name"
# Expected: trnsys-license-macos-arm64.tar.gz and trnsys-license-windows-x64.zip

Remove-Item trnsys-license-windows-x64.zip
```

## Step 3: Build and upload trnexe v0.3.0

```powershell
cd path\to\trnexe
git checkout main
git pull

npm ci
npx tauri build

Get-Item src-tauri\target\release\trnexe.exe | Select-Object Name, Length

Compress-Archive -Path src-tauri\target\release\trnexe.exe -DestinationPath trnexe-windows-x64-runtime.zip -Force
gh release upload v0.3.0 trnexe-windows-x64-runtime.zip --repo trnsys/trnexe

# Verify
gh release view v0.3.0 --repo trnsys/trnexe --json assets -q ".assets[].name"
# Expected: trnexe-macos-arm64-runtime.tar.gz and trnexe-windows-x64-runtime.zip

Remove-Item trnexe-windows-x64-runtime.zip
```

## Step 4: Assemble and publish release bundle

```powershell
cd path\to\releases
git checkout build-windows-x64
git pull

python build.py
```

Follow the instructions printed by `build.py` to tag `v19.0.0-alpha.6` and publish.

## Step 5: Test the full flow

1. Run `trn.exe` (the new v0.8.0 binary — either from the bundle or built in step 1)
2. Go through the installation flow — create a new installation
3. Open an installation, verify the detail screen shows Update/Remove actions
4. Open trnexe from the installation and run a deck

## If something fails

- **cargo/rust errors**: Make sure you're on `main` and pulled latest
- **gh permission denied**: Check `gh auth status`
- **build.py fails on download**: A previous step's upload may not have completed — verify with `gh release view`
- **trnexe LoadLibraryExW error**: Should be fixed in v0.3.0 — if it recurs, check that `engine.dll` exists in the Exe directory
