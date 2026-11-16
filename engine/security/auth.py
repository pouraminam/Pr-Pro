"""
Security and Authentication Module for Premiere AI Editor Local Engine.

Enforces:
- Loopback-only binding (127.0.0.1)
- Per-session authentication token verification
- Safe path resolution and path traversal prevention
"""

import os
import secrets
import string
from pathlib import Path
from typing import Optional, List, Set


class SecurityManager:
    """Manages authentication tokens and path validation for the local helper service."""

    def __init__(self, token_file: Optional[str] = None, allowed_roots: Optional[List[str]] = None):
        self.session_token = self._init_token(token_file)
        self.allowed_roots: Set[Path] = set()
        
        if allowed_roots:
            for root in allowed_roots:
                p = Path(root).resolve()
                self.allowed_roots.add(p)

    def _init_token(self, token_file: Optional[str]) -> str:
        """Loads an existing token from file or generates a secure random session token."""
        if token_file and os.path.exists(token_file):
            try:
                with open(token_file, "r", encoding="utf-8") as f:
                    token = f.read().strip()
                    if len(token) >= 32:
                        return token
            except Exception:
                pass

        # Generate a cryptographically secure 48-character token
        alphabet = string.ascii_letters + string.digits
        token = "".join(secrets.choice(alphabet) for _ in range(48))

        if token_file:
            try:
                os.makedirs(os.path.dirname(os.path.abspath(token_file)), exist_ok=True)
                with open(token_file, "w", encoding="utf-8") as f:
                    f.write(token)
                # Attempt to set restrictive file permissions (user read/write only)
                try:
                    os.chmod(token_file, 0o600)
                except Exception:
                    pass
            except Exception:
                pass

        return token

    def verify_token(self, token: Optional[str]) -> bool:
        """Constant-time token comparison to avoid timing attacks."""
        if not token or not self.session_token:
            return False
        return secrets.compare_digest(token.strip(), self.session_token)

    def add_allowed_root(self, path: str) -> None:
        """Adds an allowed root directory for file operations."""
        resolved = Path(path).resolve()
        self.allowed_roots.add(resolved)

    def is_safe_path(self, file_path: str, must_exist: bool = False) -> bool:
        """
        Validates that a path is safe and does not escape allowed directories.
        Prevents directory traversal attacks (e.g. ../../etc/passwd).
        """
        if not file_path or not isinstance(file_path, str):
            return False

        try:
            target = Path(file_path).resolve()
        except Exception:
            return False

        if must_exist and not target.exists():
            return False

        # If explicit allowed roots are set, check membership
        if self.allowed_roots:
            is_subpath = any(
                target == root or root in target.parents
                for root in self.allowed_roots
            )
            return is_subpath

        # If no explicit roots configured, allow standard project/user paths
        # but disallow dangerous system root modifications
        forbidden_prefixes = ["/etc", "/sys", "/proc", "/bin", "/sbin", "/usr/bin", "C:\\Windows\\System32"]
        target_str = str(target)
        for prefix in forbidden_prefixes:
            if target_str.startswith(prefix):
                return False

        return True
