"""Unit tests for Authorize.Net webhook utilities"""
import hmac
import hashlib

from app.utils.authorize_net_webhook import verify_signature


def test_verify_signature_success():
    payload = b'{"hello":"world"}'
    key = b"1234567890abcdef"
    signature = hmac.new(key, payload, hashlib.sha512).hexdigest()
    header = f"SHA512={signature}"

    assert verify_signature(header, payload, key.hex()) is True


def test_verify_signature_failure_on_bad_header():
    payload = b'{"hello":"world"}'
    key = b"1234567890abcdef"
    signature = hmac.new(key, payload, hashlib.sha512).hexdigest()
    bad_header = f"MD5={signature}"

    assert verify_signature(bad_header, payload, key.hex()) is False


def test_verify_signature_failure_on_wrong_key():
    payload = b'{"hello":"world"}'
    key = b"1234567890abcdef"
    wrong_key = b"deadbeefdeadbeef"
    signature = hmac.new(wrong_key, payload, hashlib.sha512).hexdigest()
    header = f"SHA512={signature}"

    assert verify_signature(header, payload, key.hex()) is False
