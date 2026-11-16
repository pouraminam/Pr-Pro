# Troubleshooting Guide — Premiere AI Editor

Common diagnostic procedures and solutions.

---

## 1. Helper Service Shows "Offline" in Panel

### Symptoms:
- Red status indicator in the top right of the panel displaying "Helper Offline".

### Solutions:
1. Ensure the engine helper is running. Double-click `installer\windows\start_engine.vbs` or run in terminal:
   ```bash
   python -m engine.main --port 8990
   ```
2. Verify local connectivity by opening `http://127.0.0.1:8990/health` in your web browser. You should receive a JSON response showing `"status": "ok"`.
3. Check firewall / local port restrictions: Ensure loopback communications on port 8990 are not blocked by third-party antivirus software.

---

## 2. "No Media Audio File Found"

### Symptoms:
- Alert when clicking Analyze stating no audio media path could be resolved.

### Solutions:
1. Verify that your active Premiere sequence has at least one unmuted audio clip.
2. If your audio track contains nested or synthetic audio (bars/tone), export an audio mixdown (`.wav`) and place it on track A1.

---

## 3. CUDA GPU Acceleration Not Detected

### Symptoms:
- Settings tab shows CPU mode even though an NVIDIA GPU is installed.

### Solutions:
1. The engine automatically checks for NVIDIA CUDA drivers and CTranslate2/PyTorch GPU libraries.
2. If CUDA drivers are missing or incompatible, the engine falls back to CPU mode to guarantee stable operation without crashing.
3. To enable GPU acceleration, ensure the latest NVIDIA drivers are installed.
