"""
REST API Request Router and Handlers for Premiere AI Editor Local Engine.

Handles request dispatching, parameter validation, security checks, and response serialization.
"""

import json
import os
from typing import Dict, Any, Tuple, Optional
from ..security.auth import SecurityManager
from ..audio.extractor import AudioExtractor
from ..audio.analyzer import WaveformAnalyzer
from ..transcription.models_manager import ModelsManager
from ..transcription.whisper_backend import FasterWhisperBackend, detect_hardware
from ..vad.detector import SilenceDetector
from ..translation.translator import OfflineTranslator
from ..subtitles.generator import SubtitleGenerator
from ..subtitles.remapper import TimelineTimeMapper
from ..subtitles.formats import export_to_srt, export_to_vtt, export_to_text, export_to_json
from .task_runner import TaskRunner


class RouteHandler:
    """Dispatches API requests to engine subsystems."""

    def __init__(self, security_manager: SecurityManager, models_dir: Optional[str] = None):
        self.security = security_manager
        self.models_manager = ModelsManager(models_dir=models_dir)
        self.whisper_backend = FasterWhisperBackend(models_manager=self.models_manager)
        self.silence_detector = SilenceDetector()
        self.audio_extractor = AudioExtractor()
        self.waveform_analyzer = WaveformAnalyzer()
        self.translator = OfflineTranslator(models_dir=models_dir)
        self.task_runner = TaskRunner()

    def handle_request(
        self,
        method: str,
        path: str,
        headers: Dict[str, str],
        body_data: Optional[bytes] = None,
    ) -> Tuple[int, Dict[str, Any]]:
        """Main dispatcher for HTTP requests."""
        # 1. Health check is unauthenticated for connection discovery
        if method == "GET" and path == "/health":
            return self.get_health()

        # 2. Check token authentication
        auth_token = headers.get("X-Session-Token") or headers.get("x-session-token")
        if not auth_token and "Authorization" in headers:
            auth_val = headers["Authorization"]
            if auth_val.startswith("Bearer "):
                auth_token = auth_val[7:].strip()

        if not self.security.verify_token(auth_token):
            return 401, {"error": "Unauthorized: Invalid or missing session token."}

        # Parse JSON payload if present
        body: Dict[str, Any] = {}
        if body_data and len(body_data) > 0:
            try:
                body = json.loads(body_data.decode("utf-8"))
            except Exception as e:
                return 400, {"error": f"Invalid JSON body: {e}"}

        # Route matching
        try:
            if method == "GET":
                if path == "/models":
                    return 200, {"models": self.models_manager.list_models()}
                elif path.startswith("/tasks/"):
                    task_id = path.split("/tasks/")[1]
                    task = self.task_runner.get_task(task_id)
                    if not task:
                        return 404, {"error": f"Task not found: {task_id}"}
                    return 200, task.to_dict()

            elif method == "POST":
                if path == "/models/download":
                    model_name = body.get("model", "base")
                    ok = self.models_manager.start_download(model_name)
                    return (200, {"status": "started", "model": model_name}) if ok else (400, {"error": "Download already in progress."})

                elif path == "/audio/extract":
                    return self.post_audio_extract(body)

                elif path == "/audio/waveform":
                    return self.post_audio_waveform(body)

                elif path == "/analysis/transcribe":
                    return self.post_transcribe(body)

                elif path == "/analysis/silence":
                    return self.post_silence_detection(body)

                elif path == "/analysis/quick-edit":
                    return self.post_quick_edit(body)

                elif path == "/subtitles/generate":
                    return self.post_subtitles_generate(body)

                elif path == "/subtitles/translate":
                    return self.post_subtitles_translate(body)

                elif path == "/subtitles/remap":
                    return self.post_subtitles_remap(body)

                elif path == "/subtitles/export":
                    return self.post_subtitles_export(body)

                elif path.startswith("/tasks/") and path.endswith("/cancel"):
                    task_id = path.split("/tasks/")[1].split("/cancel")[0]
                    ok = self.task_runner.cancel_task(task_id)
                    return (200, {"status": "cancelled", "task_id": task_id}) if ok else (404, {"error": "Task not found or already finished."})

                elif path == "/shutdown":
                    return 200, {"status": "shutting_down"}

            elif method == "DELETE":
                if path.startswith("/models/"):
                    model_name = path.split("/models/")[1]
                    ok = self.models_manager.delete_model(model_name)
                    return (200, {"status": "deleted", "model": model_name}) if ok else (404, {"error": "Model not found."})

            return 404, {"error": f"Endpoint not found: {method} {path}"}

        except Exception as e:
            return 500, {"error": f"Internal server error: {e}"}

    def get_health(self) -> Tuple[int, Dict[str, Any]]:
        return 200, {
            "status": "ok",
            "service": "premiere-ai-editor-helper",
            "version": "1.0.0",
            "hardware": detect_hardware(),
            "models_dir": self.models_manager.get_models_directory(),
        }

    def post_audio_extract(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        media_file = body.get("media_file")
        output_file = body.get("output_file")

        if not media_file or not output_file:
            return 400, {"error": "media_file and output_file required"}

        if not self.security.is_safe_path(media_file, must_exist=True) or not self.security.is_safe_path(output_file):
            return 403, {"error": "Access to specified path is forbidden."}

        self.audio_extractor.extract_to_16k_mono(media_file, output_file)
        dur, sr, _ = AudioExtractor.get_wav_info(output_file)
        return 200, {"status": "extracted", "output_file": output_file, "duration": dur, "sample_rate": sr}

    def post_audio_waveform(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        wav_file = body.get("wav_file")
        if not wav_file or not self.security.is_safe_path(wav_file, must_exist=True):
            return 400, {"error": "Valid wav_file path required"}

        target_points = int(body.get("target_points", 1200))
        data = self.waveform_analyzer.generate_envelope(wav_file, max_points=target_points)
        return 200, data

    def post_transcribe(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        audio_path = body.get("audio_path")
        if not audio_path or not self.security.is_safe_path(audio_path, must_exist=True):
            return 400, {"error": "Valid audio_path required"}

        model_name = body.get("model", "base")
        language = body.get("language", "auto")
        device = body.get("device", "auto")
        word_timestamps = bool(body.get("word_timestamps", True))
        beam_size = int(body.get("beam_size", 5))
        initial_prompt = body.get("initial_prompt")
        is_async = bool(body.get("async", True))

        if is_async:
            task = self.task_runner.create_task("transcription")

            def _worker(t, progress_cb):
                return self.whisper_backend.transcribe(
                    audio_path=audio_path,
                    model_name=model_name,
                    language=language,
                    device=device,
                    word_timestamps=word_timestamps,
                    beam_size=beam_size,
                    initial_prompt=initial_prompt,
                    progress_callback=progress_cb,
                )

            self.task_runner.run_async(task, _worker)
            return 202, {"task_id": task.task_id, "status": "pending"}
        else:
            result = self.whisper_backend.transcribe(
                audio_path=audio_path,
                model_name=model_name,
                language=language,
                device=device,
                word_timestamps=word_timestamps,
                beam_size=beam_size,
                initial_prompt=initial_prompt,
            )
            return 200, result

    def post_silence_detection(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        audio_path = body.get("audio_path")
        if not audio_path or not self.security.is_safe_path(audio_path, must_exist=True):
            return 400, {"error": "Valid audio_path required"}

        mode = body.get("mode", "hybrid")
        preset = body.get("preset", "balanced")
        custom_params = body.get("custom_params")
        preserve_breathing = bool(body.get("preserve_breathing", True))
        transcript_segments = body.get("transcript_segments")

        result = self.silence_detector.detect(
            wav_path=audio_path,
            mode=mode,
            preset=preset,
            custom_params=custom_params,
            transcript_segments=transcript_segments,
            preserve_breathing=preserve_breathing,
        )
        return 200, result

    def post_quick_edit(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """Executes full Quick Edit pipeline: transcribe -> detect silence -> build cut plan."""
        audio_path = body.get("audio_path")
        if not audio_path or not self.security.is_safe_path(audio_path, must_exist=True):
            return 400, {"error": "Valid audio_path required"}

        task = self.task_runner.create_task("quick_edit")

        def _worker(t, progress_cb):
            progress_cb(10.0, "Transcribing speech...")
            trans_res = self.whisper_backend.transcribe(
                audio_path=audio_path,
                model_name=body.get("model", "base"),
                language=body.get("language", "auto"),
                progress_callback=lambda p, s: progress_cb(10.0 + p * 0.5, s),
            )

            progress_cb(65.0, "Analyzing audio and detecting pauses...")
            silence_res = self.silence_detector.detect(
                wav_path=audio_path,
                mode="hybrid",
                preset=body.get("preset", "balanced"),
                transcript_segments=trans_res.get("segments", []),
            )

            progress_cb(85.0, "Generating subtitles and time mapping...")
            sub_gen = SubtitleGenerator()
            subs = sub_gen.generate(trans_res.get("segments", []), language=trans_res.get("language", "en"))

            approved_cuts = [s for s in silence_res["silence_intervals"] if s["enabled"] and not s["protected"]]
            time_mapper = TimelineTimeMapper(approved_cuts)
            remapped_subs = time_mapper.remap_subtitles(subs)

            progress_cb(100.0, "Quick Edit plan ready.")

            return {
                "transcription": trans_res,
                "silence": silence_res,
                "subtitles": subs,
                "remapped_subtitles": remapped_subs,
                "proposed_cuts": approved_cuts,
                "summary": {
                    "original_duration": silence_res["total_duration"],
                    "edited_duration": silence_res["estimated_edited_duration"],
                    "time_saved_percent": silence_res["time_saved_percent"],
                    "cut_count": len(approved_cuts),
                }
            }

        self.task_runner.run_async(task, _worker)
        return 202, {"task_id": task.task_id, "status": "pending"}

    def post_subtitles_generate(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        segments = body.get("segments", [])
        lang = body.get("language", "en")
        opts = body.get("options", {})

        generator = SubtitleGenerator(
            max_chars_per_line=int(opts.get("max_chars_per_line", 42)),
            max_lines_per_caption=int(opts.get("max_lines_per_caption", 2)),
            min_duration=float(opts.get("min_duration", 1.0)),
            max_duration=float(opts.get("max_duration", 6.0)),
            min_gap=float(opts.get("min_gap", 0.05)),
            max_reading_speed_cps=float(opts.get("max_reading_speed_cps", 21.0)),
        )
        subtitles = generator.generate(segments, language=lang)
        return 200, {"subtitles": subtitles, "count": len(subtitles)}

    def post_subtitles_translate(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        subtitles = body.get("subtitles", [])
        src = body.get("source_lang", "fa")
        tgt = body.get("target_lang", "en")

        translated = self.translator.translate_subtitles(subtitles, source_lang=src, target_lang=tgt)
        return 200, {"subtitles": translated, "source_lang": src, "target_lang": tgt}

    def post_subtitles_remap(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        subtitles = body.get("subtitles", [])
        removed = body.get("removed_intervals", [])

        mapper = TimelineTimeMapper(removed)
        remapped = mapper.remap_subtitles(subtitles)
        return 200, {"subtitles": remapped, "count": len(remapped)}

    def post_subtitles_export(self, body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        subtitles = body.get("subtitles", [])
        fmt = body.get("format", "srt").lower()
        output_path = body.get("output_path")
        rtl_markers = bool(body.get("rtl_markers", True))

        if fmt == "srt":
            content = export_to_srt(subtitles, add_rtl_markers=rtl_markers)
        elif fmt == "vtt":
            content = export_to_vtt(subtitles, add_rtl_markers=rtl_markers)
        elif fmt == "json":
            content = export_to_json(subtitles)
        elif fmt == "txt":
            content = export_to_text(subtitles)
        else:
            return 400, {"error": f"Unsupported format: {fmt}. Must be srt, vtt, json, or txt."}

        if output_path:
            if not self.security.is_safe_path(output_path):
                return 403, {"error": "Invalid output path"}
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

        return 200, {"format": fmt, "content": content, "saved_to": output_path}
