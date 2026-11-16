#!/usr/bin/env python3
"""
Packages Premiere AI Editor into an installable Adobe UXP .ccx package.

A .ccx package is a zip container adhering to Adobe UXP packaging specifications.
"""

import json
import os
import zipfile
from pathlib import Path


def package_ccx(plugin_dir: str, output_ccx: str) -> str:
    plugin_path = Path(plugin_dir).resolve()
    out_path = Path(output_ccx).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    manifest_file = plugin_path / "manifest.json"
    if not manifest_file.exists():
        raise FileNotFoundError(f"manifest.json not found in {plugin_path}")

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    version = manifest.get("version", "1.0.0")
    print(f"Packaging Premiere AI Editor v{version} into {out_path.name}...")

    # Exclude files/patterns
    exclude_patterns = [".git", "__pycache__", ".DS_Store", "node_modules", ".tmp"]

    with zipfile.ZipFile(str(out_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(str(plugin_path)):
            # Prune excluded directories
            dirs[:] = [d for d in dirs if not any(p in d for p in exclude_patterns)]

            for file in files:
                if any(file.endswith(p) for p in [".pyc", ".tmp", ".log"]):
                    continue
                file_abs = Path(root) / file
                arcname = file_abs.relative_to(plugin_path)
                zf.write(str(file_abs), str(arcname))

    print(f"Successfully created CCX package: {out_path} ({out_path.stat().st_size} bytes)")
    return str(out_path)


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    plugin_src = repo_root / "plugin"
    dist_dir = repo_root / "dist"
    ccx_file = dist_dir / "premiere-ai-editor-1.0.0.ccx"

    package_ccx(str(plugin_src), str(ccx_file))
