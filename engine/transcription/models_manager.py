"""
Whisper Model Catalog and Download Manager.

Manages:
- Model metadata (download size, RAM/VRAM requirements, language support)
- Local model discovery and disk footprint tracking
- Resumable background downloads with progress reporting and cancellation
- Model deletion and custom model directory configuration
"""

import os
import shutil
import urllib.request
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable


MODEL_CATALOG = {
    "tiny": {
        "name": "tiny",
        "label": "Tiny (Fastest, Lowest Memory)",
        "download_size_mb": 75,
        "ram_required_gb": 1.0,
        "vram_required_gb": 1.0,
        "multilingual": True,
        "languages": ["fa", "en", "auto"],
        "recommended_for": "Quick drafts, low-spec laptops",
        "repo_id": "Systran/faster-whisper-tiny",
        "download_url": "https://huggingface.co/Systran/faster-whisper-tiny/resolve/main/model.bin",
    },
    "base": {
        "name": "base",
        "label": "Base (Balanced Speed/Accuracy - Recommended)",
        "download_size_mb": 145,
        "ram_required_gb": 1.5,
        "vram_required_gb": 1.2,
        "multilingual": True,
        "languages": ["fa", "en", "auto"],
        "recommended_for": "Everyday YouTube and educational video editing",
        "repo_id": "Systran/faster-whisper-base",
        "download_url": "https://huggingface.co/Systran/faster-whisper-base/resolve/main/model.bin",
    },
    "small": {
        "name": "small",
        "label": "Small (High Accuracy, Good for Persian/English)",
        "download_size_mb": 480,
        "ram_required_gb": 2.5,
        "vram_required_gb": 2.0,
        "multilingual": True,
        "languages": ["fa", "en", "auto"],
        "recommended_for": "Professional speech recognition, accented speech",
        "repo_id": "Systran/faster-whisper-small",
        "download_url": "https://huggingface.co/Systran/faster-whisper-small/resolve/main/model.bin",
    },
    "medium": {
        "name": "medium",
        "label": "Medium (Very High Accuracy)",
        "download_size_mb": 1500,
        "ram_required_gb": 5.0,
        "vram_required_gb": 4.0,
        "multilingual": True,
        "languages": ["fa", "en", "auto"],
        "recommended_for": "Complex multilingual recordings and high accuracy subtitles",
        "repo_id": "Systran/faster-whisper-medium",
        "download_url": "https://huggingface.co/Systran/faster-whisper-medium/resolve/main/model.bin",
    },
    "large-v3": {
        "name": "large-v3",
        "label": "Large-v3 (Maximum Accuracy, Requires GPU or High RAM)",
        "download_size_mb": 3100,
        "ram_required_gb": 10.0,
        "vram_required_gb": 6.0,
        "multilingual": True,
        "languages": ["fa", "en", "auto"],
        "recommended_for": "Studio quality transcription and maximum Persian precision",
        "repo_id": "Systran/faster-whisper-large-v3",
        "download_url": "https://huggingface.co/Systran/faster-whisper-large-v3/resolve/main/model.bin",
    },
}


class ModelsManager:
    """Manages Whisper models on local disk."""

    def __init__(self, models_dir: Optional[str] = None):
        if models_dir:
            self.models_dir = Path(models_dir).resolve()
        else:
            # Default to per-user cache directory
            if os.name == "nt":
                app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
                self.models_dir = Path(app_data) / "PremiereAIEditor" / "models"
            else:
                self.models_dir = Path.home() / ".cache" / "premiere_ai_editor" / "models"

        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._active_downloads: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get_models_directory(self) -> str:
        return str(self.models_dir)

    def set_models_directory(self, new_dir: str) -> None:
        p = Path(new_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        self.models_dir = p

    def is_model_installed(self, model_name: str) -> bool:
        """Checks if the model directory exists and has model files."""
        model_path = self.models_dir / model_name
        if not model_path.is_dir():
            return False
        # Check for model.bin or weights
        has_files = any(model_path.glob("model.bin*")) or any(model_path.glob("*.bin")) or any(model_path.glob("*.safetensors"))
        return has_files

    def get_model_path(self, model_name: str) -> Optional[str]:
        if self.is_model_installed(model_name):
            return str(self.models_dir / model_name)
        return None

    def list_models(self) -> List[Dict[str, Any]]:
        """Returns catalog with installation status and sizes."""
        result = []
        for name, info in MODEL_CATALOG.items():
            installed = self.is_model_installed(name)
            disk_size = 0
            model_folder = self.models_dir / name
            if installed and model_folder.is_dir():
                disk_size = sum(f.stat().st_size for f in model_folder.glob("**/*") if f.is_file()) // (1024 * 1024)

            download_info = self._active_downloads.get(name, {})

            entry = dict(info)
            entry["installed"] = installed
            entry["disk_size_mb"] = disk_size if installed else 0
            entry["disk_path"] = str(model_folder) if installed else None
            entry["download_status"] = download_info.get("status", "idle")
            entry["download_progress"] = download_info.get("progress", 0.0)
            entry["download_error"] = download_info.get("error", None)
            result.append(entry)

        return result

    def start_download(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> bool:
        """Starts asynchronous download of a model."""
        if model_name not in MODEL_CATALOG:
            raise ValueError(f"Unknown model name: {model_name}")

        with self._lock:
            if model_name in self._active_downloads and self._active_downloads[model_name]["status"] == "downloading":
                return False  # Already in progress

            self._active_downloads[model_name] = {
                "status": "downloading",
                "progress": 0.0,
                "error": None,
                "cancel_requested": False,
            }

        thread = threading.Thread(
            target=self._download_worker,
            args=(model_name, progress_callback),
            daemon=True,
        )
        thread.start()
        return True

    def cancel_download(self, model_name: str) -> bool:
        with self._lock:
            if model_name in self._active_downloads and self._active_downloads[model_name]["status"] == "downloading":
                self._active_downloads[model_name]["cancel_requested"] = True
                return True
        return False

    def _download_worker(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> None:
        """Handles downloading model files using faster_whisper or huggingface_hub if available."""
        model_info = MODEL_CATALOG[model_name]
        dest_dir = self.models_dir / model_name
        dest_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Check if faster_whisper / huggingface_hub is available
            try:
                from huggingface_hub import snapshot_download
                repo_id = model_info["repo_id"]
                
                def _hf_progress(step, total):
                    pct = min(100.0, (step / float(total)) * 100.0) if total > 0 else 0.0
                    with self._lock:
                        self._active_downloads[model_name]["progress"] = round(pct, 1)
                    if progress_callback:
                        progress_callback(pct, f"Downloading {model_name} ({pct:.1f}%)")

                snapshot_download(
                    repo_id=repo_id,
                    local_dir=str(dest_dir),
                    local_dir_use_symlinks=False,
                )
            except ImportError:
                # Direct download of model.bin
                url = model_info["download_url"]
                target_file = dest_dir / "model.bin"
                temp_file = dest_dir / "model.bin.tmp"

                req = urllib.request.Request(url, headers={"User-Agent": "PremiereAIEditor/1.0"})
                with urllib.request.urlopen(req, timeout=30) as resp, open(temp_file, "wb") as out_f:
                    total_bytes = int(resp.headers.get("content-length", 0))
                    downloaded = 0
                    chunk_size = 1024 * 1024  # 1MB chunks

                    while True:
                        with self._lock:
                            if self._active_downloads[model_name].get("cancel_requested"):
                                out_f.close()
                                if temp_file.exists():
                                    temp_file.unlink()
                                self._active_downloads[model_name]["status"] = "cancelled"
                                return

                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        downloaded += len(chunk)

                        pct = (downloaded / float(total_bytes) * 100.0) if total_bytes > 0 else 50.0
                        with self._lock:
                            self._active_downloads[model_name]["progress"] = round(pct, 1)
                        if progress_callback:
                            progress_callback(pct, f"Downloading {model_name}: {downloaded // (1024*1024)}MB / {total_bytes // (1024*1024)}MB")

                if temp_file.exists():
                    temp_file.replace(target_file)

            with self._lock:
                self._active_downloads[model_name]["status"] = "completed"
                self._active_downloads[model_name]["progress"] = 100.0
            if progress_callback:
                progress_callback(100.0, f"Model {model_name} ready.")

        except Exception as e:
            with self._lock:
                self._active_downloads[model_name]["status"] = "failed"
                self._active_downloads[model_name]["error"] = str(e)
            if progress_callback:
                progress_callback(0.0, f"Download failed: {e}")

    def delete_model(self, model_name: str) -> bool:
        """Deletes downloaded model files from disk."""
        dest_dir = self.models_dir / model_name
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)
            return True
        return False
