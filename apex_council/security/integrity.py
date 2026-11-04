from __future__ import annotations

import hashlib
import hmac
import os
import re
from typing import Optional, Tuple

# Default sovereign signing key; can be overridden via APEX_SIGNING_KEY environment variable
DEFAULT_SIGNING_KEY = os.getenv("APEX_SIGNING_KEY", "sovereign-apex-cryptographic-master-key-sha512").encode("utf-8")

SIG_PATTERN = re.compile(r"# APEX-SIG-SHA512:\s*([a-f0-9]{128})\r?", re.MULTILINE)


class CodeIntegritySigner:
    """HMAC-SHA512 Cryptographic Code Signing & Anti-Tamper Engine.

    Attaches tamper-evident cryptographic attestation to synthesized code,
    preventing malicious payload injection and runtime unauthorized modifications.
    """

    @staticmethod
    def sign_code(code: str, secret_key: Optional[bytes] = None) -> str:
        key = secret_key or DEFAULT_SIGNING_KEY

        # Strip any existing signature line
        clean_code = SIG_PATTERN.sub("", code).strip()

        # Compute HMAC-SHA512
        sig = hmac.new(key, clean_code.encode("utf-8"), hashlib.sha512).hexdigest()

        return f"# APEX-SIG-SHA512: {sig}\n{clean_code}\n"

    @staticmethod
    def verify_signature(signed_code: str, secret_key: Optional[bytes] = None) -> Tuple[bool, str]:
        key = secret_key or DEFAULT_SIGNING_KEY

        match = SIG_PATTERN.search(signed_code)
        if not match:
            return False, "Missing cryptographic signature (# APEX-SIG-SHA512)"

        claimed_sig = match.group(1)
        clean_code = SIG_PATTERN.sub("", signed_code).strip()

        expected_sig = hmac.new(key, clean_code.encode("utf-8"), hashlib.sha512).hexdigest()

        # Constant-time comparison to prevent side-channel timing attacks
        is_valid = hmac.compare_digest(claimed_sig, expected_sig)
        if not is_valid:
            return False, "Tampered Code: Cryptographic signature mismatch! Content was altered after signing."

        return True, "Cryptographic signature verified. Code integrity is authentic."
