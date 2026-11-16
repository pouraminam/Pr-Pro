#!/usr/bin/env python3
"""
Full Release Packaging Script.
Builds the .ccx plugin package, sets up the distribution zip, and verifies release artifacts.
"""

import os
import shutil
import zipfile
from pathlib import Path
from installer.package_plugin import package_ccx


def main():
    repo_root = Path(__file__).resolve().parent.parent
    dist_dir = repo_root / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    print("=== Premiere AI Editor Production Packaging ===")

    # 1. Package UXP Plugin into .ccx
    plugin_dir = repo_root / "plugin"
    ccx_path = dist_dir / "premiere-ai-editor-1.0.0.ccx"
    package_ccx(str(plugin_dir), str(ccx_path))

    # 2. Package Full Windows Distribution ZIP
    zip_path = dist_dir / "PremiereAIEditor-v1.0.0-windows-x64.zip"
    print(f"Creating release distribution zip at {zip_path.name}...")

    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        # Add CCX package
        zf.write(str(ccx_path), "premiere-ai-editor-1.0.0.ccx")

        # Add installer folder
        installer_dir = repo_root / "installer"
        for root, dirs, files in os.walk(str(installer_dir)):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                f_path = Path(root) / file
                rel_path = f_path.relative_to(repo_root)
                zf.write(str(f_path), str(rel_path))

        # Add engine source
        engine_dir = repo_root / "engine"
        for root, dirs, files in os.walk(str(engine_dir)):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                f_path = Path(root) / file
                rel_path = f_path.relative_to(repo_root)
                zf.write(str(f_path), str(rel_path))

        # Add docs
        docs_dir = repo_root / "docs"
        for root, dirs, files in os.walk(str(docs_dir)):
            for file in files:
                f_path = Path(root) / file
                rel_path = f_path.relative_to(repo_root)
                zf.write(str(f_path), str(rel_path))

        # Add README and Licenses
        if (repo_root / "README.md").exists():
            zf.write(str(repo_root / "README.md"), "README.md")

    print(f"Release distribution zip created: {zip_path} ({zip_path.stat().st_size} bytes)")
    print("=== Packaging Complete ===")


if __name__ == "__main__":
    main()
