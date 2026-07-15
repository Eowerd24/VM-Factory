"""SSH transport must pin host keys, never auto-trust or use /dev/null as the
known_hosts sink (locked security floor: no AutoAddPolicy/accept-new, no
UserKnownHostsFile=/dev/null; UCC-Standards-and-Layout-Reference.md §15)."""
import os
from pathlib import Path
import pytest
from library.transport import SSHTransportBackend, _default_known_hosts_path


def test_default_opts_reject_unknown_hosts(tmp_path, monkeypatch):
    monkeypatch.delenv("VM_FACTORY_KNOWN_HOSTS", raising=False)
    monkeypatch.setenv("NODEFACTORY_STATE", str(tmp_path))
    backend = SSHTransportBackend()
    opts = backend._get_ssh_opts()
    assert "StrictHostKeyChecking=accept-new" not in opts
    assert "UserKnownHostsFile=/dev/null" not in opts
    assert "StrictHostKeyChecking=yes" in opts
    assert any(o.startswith("UserKnownHostsFile=") and o != "UserKnownHostsFile=/dev/null" for o in opts)


def test_known_hosts_path_explicit_constructor_arg(tmp_path):
    pinned = tmp_path / "custom" / "known_hosts"
    backend = SSHTransportBackend(known_hosts_path=pinned)
    assert backend.known_hosts_path == pinned
    assert f"UserKnownHostsFile={pinned}" in backend._get_ssh_opts()


def test_known_hosts_path_from_env_var(tmp_path, monkeypatch):
    pinned = tmp_path / "env-known-hosts"
    monkeypatch.setenv("VM_FACTORY_KNOWN_HOSTS", str(pinned))
    backend = SSHTransportBackend()
    assert backend.known_hosts_path == pinned


def test_known_hosts_default_derives_from_state_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("VM_FACTORY_KNOWN_HOSTS", raising=False)
    monkeypatch.setenv("NODEFACTORY_STATE", str(tmp_path))
    assert _default_known_hosts_path() == tmp_path / "ssh" / "known_hosts"


def test_env_override_takes_precedence_over_state_dir(tmp_path, monkeypatch):
    pinned = tmp_path / "elsewhere" / "known_hosts"
    monkeypatch.setenv("VM_FACTORY_KNOWN_HOSTS", str(pinned))
    monkeypatch.setenv("NODEFACTORY_STATE", str(tmp_path / "state"))
    assert _default_known_hosts_path() == pinned
