"""
Integration Test for Local Processing Engine HTTP/REST API.

Spawns EngineServer in a background thread on a test port,
makes authenticated HTTP requests to all core endpoints, and validates responses.
"""

import json
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from engine.service.app import EngineServer


class TestEngineAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_port = 8998
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.token_file = str(Path(cls.temp_dir.name) / "test.token")
        cls.fixture_wav = str(Path(__file__).resolve().parent.parent / "fixtures" / "test_speech_and_silence.wav")

        cls.server = EngineServer(
            host="127.0.0.1",
            port=cls.test_port,
            token_file=cls.token_file,
            models_dir=str(Path(cls.temp_dir.name) / "models"),
        )

        cls.server_thread = threading.Thread(target=cls.server.start, daemon=True)
        cls.server_thread.start()

        # Wait for server ready
        ready = False
        for _ in range(20):
            try:
                req = urllib.request.Request(f"http://127.0.0.1:{cls.test_port}/health")
                with urllib.request.urlopen(req, timeout=1.0) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except Exception:
                time.sleep(0.1)

        if not ready:
            raise RuntimeError("EngineServer failed to start on test port.")

        with open(cls.token_file, "r", encoding="utf-8") as f:
            cls.token = f.read().strip()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
        cls.temp_dir.cleanup()

    def _api_request(self, method, path, payload=None, token=None):
        url = f"http://127.0.0.1:{self.test_port}{path}"
        headers = {"Content-Type": "application/json"}
        auth_token = token if token is not None else self.token
        if auth_token:
            headers["X-Session-Token"] = auth_token

        data = json.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        with urllib.request.urlopen(req, timeout=10.0) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)

    def test_01_health_unauthenticated(self):
        status, data = self._api_request("GET", "/health", token="")
        self.assertEqual(status, 200)
        self.assertEqual(data["status"], "ok")
        self.assertIn("hardware", data)

    def test_02_auth_rejected_with_invalid_token(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self._api_request("GET", "/models", token="invalid_token")
        self.assertEqual(cm.exception.code, 401)

    def test_03_get_models_catalog(self):
        status, data = self._api_request("GET", "/models")
        self.assertEqual(status, 200)
        self.assertIn("models", data)
        self.assertGreater(len(data["models"]), 0)

    def test_04_silence_analysis_endpoint(self):
        payload = {
            "audio_path": self.fixture_wav,
            "mode": "fast",
            "preset": "balanced",
        }
        status, data = self._api_request("POST", "/analysis/silence", payload)
        self.assertEqual(status, 200)
        self.assertIn("silence_intervals", data)
        self.assertGreater(len(data["silence_intervals"]), 0)

    def test_05_subtitles_generate_and_export_pipeline(self):
        # 1. Generate subtitles from mock segments
        gen_payload = {
            "segments": [
                {
                    "id": 1,
                    "start": 0.5,
                    "end": 2.5,
                    "text": "Hello world and welcome to this video.",
                },
                {
                    "id": 2,
                    "start": 3.0,
                    "end": 5.0,
                    "text": "This is the second subtitle segment.",
                },
            ],
            "language": "en",
        }
        status, gen_res = self._api_request("POST", "/subtitles/generate", gen_payload)
        self.assertEqual(status, 200)
        subs = gen_res["subtitles"]
        self.assertEqual(len(subs), 2)

        # 2. Translate to Persian
        trans_payload = {
            "subtitles": subs,
            "source_lang": "en",
            "target_lang": "fa",
        }
        status, trans_res = self._api_request("POST", "/subtitles/translate", trans_payload)
        self.assertEqual(status, 200)
        fa_subs = trans_res["subtitles"]
        self.assertEqual(len(fa_subs), 2)

        # 3. Remap across a cut (cut from 2.5 to 2.9)
        remap_payload = {
            "subtitles": fa_subs,
            "removed_intervals": [{"start": 2.5, "end": 2.9}],
        }
        status, remap_res = self._api_request("POST", "/subtitles/remap", remap_payload)
        self.assertEqual(status, 200)
        remapped = remap_res["subtitles"]
        self.assertEqual(len(remapped), 2)
        # Second caption start was 3.0 -> 3.0 - 0.4 = 2.6
        self.assertEqual(remapped[1]["start"], 2.6)

        # 4. Export to SRT
        export_payload = {
            "subtitles": remapped,
            "format": "srt",
        }
        status, export_res = self._api_request("POST", "/subtitles/export", export_payload)
        self.assertEqual(status, 200)
        self.assertIn("content", export_res)
        self.assertIn("00:00:00,500 -->", export_res["content"])


if __name__ == "__main__":
    unittest.main()
