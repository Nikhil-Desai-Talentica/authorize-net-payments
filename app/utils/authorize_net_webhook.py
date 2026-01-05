"""Utilities for Authorize.Net webhook verification"""
import hmac
import hashlib
from typing import Optional


def verify_signature(signature_header: Optional[str], payload: bytes, signature_key_hex: str) -> bool:
    """
    Verify Authorize.Net webhook signature.

    Header value format: "SHA512=<hex digest>"
    Digest is HMAC-SHA512 over the raw payload using the signature key (hex string) as key.
    """
    if not signature_header or not signature_key_hex:
        return False

    parts = signature_header.split("=", 1)
    if len(parts) != 2 or parts[0].lower() != "sha512":
        return False

    try:
        key = bytes.fromhex(signature_key_hex)
    except ValueError:
        return False

    expected = hmac.new(key, payload, hashlib.sha512).hexdigest()
    provided = parts[1].strip().lower()
    return hmac.compare_digest(expected, provided)
