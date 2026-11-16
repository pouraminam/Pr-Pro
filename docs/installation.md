# Installation and Deployment Guide — Premiere AI Editor

This guide covers setup and installation for **Windows 11 x64** and Adobe Premiere Pro (v24.x / v25.x).

---

## 1. System Requirements

### Minimum Requirements:
- **Operating System:** Windows 11 (x64) or Windows 10 (version 21H2+)
- **Host Application:** Adobe Premiere Pro v24.0 or newer (v24.x, v25.x)
- **Processor:** Intel Core i5 (8th Gen+) or AMD Ryzen 5 (3000 series+)
- **Memory (RAM):** 16 GB RAM
- **Storage:** 2 GB available SSD space (for application and base Whisper model)

### Recommended for Accelerated Performance:
- **GPU:** NVIDIA GeForce RTX 3060 / 4060 or higher (with 6GB+ VRAM and CUDA support)
- **Memory:** 32 GB RAM

---

## 2. Graphical GUI Installation (Recommended)

1. Download the release package: `PremiereAIEditor-v1.0.0-windows-x64.zip`.
2. Extract the archive to any local folder (e.g. `C:\Tools\PremiereAIEditor`).
3. Right-click `installer\windows\install.ps1` and choose **Run with PowerShell**.
4. The setup window will verify system prerequisites:
   - Verifies Windows version compatibility.
   - Detects Adobe Premiere Pro installation paths.
   - Verifies the local helper runtime.
5. Click **Install Now**.
6. The installer copies the UXP extension to:
   ```
   %APPDATA%\Adobe\UXP\Plugins\External\com.premiere.ai.editor
   ```
   and creates a desktop shortcut: **Premiere AI Editor Engine**.
7. Launch Adobe Premiere Pro. In the top menu, navigate to:
   ```
   Window -> Extensions -> Premiere AI Editor
   ```
8. The dockable panel will open.

---

## 3. Alternative: Installation via CCX Package

Adobe's supported plugin package (`.ccx`) is located at:
```
dist\premiere-ai-editor-1.0.0.ccx
```
To install via Adobe Creative Cloud Desktop:
1. Double-click `premiere-ai-editor-1.0.0.ccx`.
2. The Adobe Unified Plugin Installer Agent (UPIP) or Creative Cloud Desktop will prompt for confirmation.
3. Click **Install**.
4. Launch the local engine helper service by running `start_engine.vbs` or `start_engine.bat`.

---

## 4. Alternative: Developer / UXP Developer Tool (UDT)

If you are developing or testing:
1. Open **Adobe UXP Developer Tool** (UDT).
2. Click **Add Existing Plugin**.
3. Select `plugin\manifest.json`.
4. Click **Load** to load the plugin directly into your active Premiere Pro session.

---

## 5. Starting the Local Helper Service

The local helper service runs on `http://127.0.0.1:8990`.
- **Silent Background Launch:** Double-click `installer\windows\start_engine.vbs`.
- **Console Launch (with visible logs):** Double-click `installer\windows\start_engine.bat` or run:
  ```bash
  python -m engine.main --port 8990
  ```
- **Service Verification:**
  Open a browser or run curl:
  ```bash
  curl http://127.0.0.1:8990/health
  ```
  Response:
  ```json
  {
    "status": "ok",
    "service": "premiere-ai-editor-helper",
    "version": "1.0.0",
    "hardware": {
      "has_cuda": true,
      "gpu_name": "NVIDIA GeForce RTX 4070",
      "recommended_device": "cuda"
    }
  }
  ```

---

## 6. Uninstallation

To remove the plugin:
1. Close Adobe Premiere Pro.
2. Delete the plugin directory:
   ```
   %APPDATA%\Adobe\UXP\Plugins\External\com.premiere.ai.editor
   ```
3. Delete the local cache and models folder if no longer needed:
   ```
   %LOCALAPPDATA%\PremiereAIEditor
   ```
