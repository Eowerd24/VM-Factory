"""Vault must fail closed: unknown refs refuse, never fabricate a token
(locked "fail-open is unacceptable"; SPEC-001 §K.3.10)."""
import pytest
from library.credentials import VaultAdapter, CredentialError


def test_unknown_reference_refuses():
    with pytest.raises(CredentialError):
        VaultAdapter.get_secret("some/unknown/ref")


def test_no_dummy_token_fabricated():
    try:
        secret = VaultAdapter.get_secret("github/deploy-key")
    except CredentialError:
        secret = None
    assert secret is None or not secret.startswith("ghp_test_token_for_")


def test_explicit_mock_still_works():
    assert VaultAdapter.get_secret("mock:test-token") == "ghp_mock_token_test-token"


def test_env_prefix_requires_present_var(monkeypatch):
    monkeypatch.delenv("UCC_ABSENT_VAR", raising=False)
    with pytest.raises(CredentialError):
        VaultAdapter.get_secret("env:UCC_ABSENT_VAR")
