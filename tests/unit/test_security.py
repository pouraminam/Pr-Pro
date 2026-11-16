"""
Unit Tests for Security and Session Authentication.
"""

import os
import tempfile
import unittest
from engine.security.auth import SecurityManager


class TestSecurity(unittest.TestCase):

    def test_session_token_generation_and_verification(self):
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            token_path = tf.name

        try:
            sec = SecurityManager(token_file=token_path)
            self.assertGreaterEqual(len(sec.session_token), 32)

            # Verification matches
            self.assertTrue(sec.verify_token(sec.session_token))

            # Rejects bad tokens
            self.assertFalse(sec.verify_token("invalid_token"))
            self.assertFalse(sec.verify_token(""))
            self.assertFalse(sec.verify_token(None))
        finally:
            if os.path.exists(token_path):
                os.remove(token_path)

    def test_path_traversal_prevention(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sec = SecurityManager(allowed_roots=[temp_dir])

            # Path inside allowed root is safe
            safe_file = os.path.join(temp_dir, "test.wav")
            with open(safe_file, "w") as f:
                f.write("test")
            self.assertTrue(sec.is_safe_path(safe_file))

            # Path traversal outside allowed root is blocked
            traversal = os.path.join(temp_dir, "..", "..", "etc", "passwd")
            self.assertFalse(sec.is_safe_path(traversal))

            # Dangerous system paths blocked
            self.assertFalse(sec.is_safe_path("/etc/shadow"))
            self.assertFalse(sec.is_safe_path("C:\\Windows\\System32\\cmd.exe"))


if __name__ == "__main__":
    unittest.main()
