import sqlite3
import json
import os
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime, timezone
from library.models import CredentialRecord, CredentialStatus

class CredentialError(Exception):
    """Raised for any credential management or vault errors."""
    pass

class VaultAdapter:
    """Adapts secret retrieval from underlying vault providers (Mock/Pass/Env)."""

    @staticmethod
    def get_secret(vault_ref: str) -> str:
        """Retrieves the actual secret value based on a reference string."""
        # Fail-closed lookup strategy: only explicit env: and mock: references
        # resolve; every unprefixed or unknown reference raises below.
        if vault_ref.startswith("env:"):
            env_var = vault_ref.split(":", 1)[1]
            val = os.environ.get(env_var)
            if not val:
                raise CredentialError(f"Environment variable '{env_var}' not found for ref '{vault_ref}'")
            return val
        elif vault_ref.startswith("mock:"):
            # Explicit mock backend only. Token fabrication is impossible for
            # any reference that is not explicitly marked mock.
            return f"ghp_mock_token_{vault_ref.split(':', 1)[1]}"

        # Fail closed. An unresolved or unprefixed reference must refuse, never
        # fabricate a dummy token or silently fall back to the ambient
        # environment (locked: "fail-open is unacceptable"; SPEC-001 §K.3.10,
        # §A.3.4). The caller receives a typed CredentialError.
        raise CredentialError(
            f"Unresolved vault reference '{vault_ref}'. Use an explicit 'env:' "
            f"or 'mock:' prefix; refusing rather than fabricating a token."
        )


class CredentialManager:
    """Manages credential metadata via SQLite and handles vault-backed injection."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initializes the SQLite metadata table if it does not exist."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS credentials (
                        id TEXT PRIMARY KEY,
                        kind TEXT NOT NULL,
                        repo TEXT NOT NULL,
                        node TEXT NOT NULL,
                        last4 TEXT NOT NULL,
                        expires TEXT NOT NULL,
                        scopes TEXT NOT NULL,
                        status TEXT NOT NULL,
                        strapped_at TEXT,
                        vault_ref TEXT NOT NULL
                    )
                """)
                conn.commit()
        except Exception as e:
            raise CredentialError(f"Failed to initialize credential metadata DB: {e}")

    def create(self, cred_id: str, kind: str, repo: str, node: str, last4: str, expires: str, scopes: List[str], vault_ref: str) -> CredentialRecord:
        """Saves new credential metadata to SQLite."""
        record = CredentialRecord(
            id=cred_id,
            kind=kind,
            repo=repo,
            node=node,
            last4=last4,
            expires=expires,
            scopes=scopes,
            status=CredentialStatus.SCRUBBED,
            vault_ref=vault_ref
        )
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO credentials (id, kind, repo, node, last4, expires, scopes, status, strapped_at, vault_ref)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.id,
                        record.kind,
                        record.repo,
                        record.node,
                        record.last4,
                        record.expires,
                        json.dumps(record.scopes),
                        record.status.value,
                        record.strapped_at,
                        record.vault_ref
                    )
                )
                conn.commit()
            return record
        except sqlite3.IntegrityError:
            raise CredentialError(f"Credential ID '{cred_id}' already exists")
        except Exception as e:
            raise CredentialError(f"Failed to write credential to DB: {e}")

    def get(self, cred_id: str) -> Optional[CredentialRecord]:
        """Retrieves credential metadata by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, kind, repo, node, last4, expires, scopes, status, strapped_at, vault_ref FROM credentials WHERE id = ?",
                    (cred_id,)
                )
                row = cursor.fetchone()
                if not row:
                    return None
                
                return CredentialRecord(
                    id=row[0],
                    kind=row[1],
                    repo=row[2],
                    node=row[3],
                    last4=row[4],
                    expires=row[5],
                    scopes=json.loads(row[6]),
                    status=CredentialStatus(row[7]),
                    strapped_at=row[8],
                    vault_ref=row[9]
                )
        except Exception as e:
            raise CredentialError(f"Failed to query DB for '{cred_id}': {e}")

    def strap(self, cred_id: str) -> Tuple[CredentialRecord, str]:
        """Marks the credential as active/strapped and retrieves the secret from the vault."""
        record = self.get(cred_id)
        if not record:
            raise CredentialError(f"Credential not found: {cred_id}")

        secret_value = VaultAdapter.get_secret(record.vault_ref)
        now_utc = datetime.now(timezone.utc).isoformat()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE credentials SET status = ?, strapped_at = ? WHERE id = ?",
                    (CredentialStatus.STRAPPED.value, now_utc, cred_id)
                )
                conn.commit()
            record.status = CredentialStatus.STRAPPED
            record.strapped_at = now_utc
            return record, secret_value
        except Exception as e:
            raise CredentialError(f"Failed to update credential status to strapped: {e}")

    def scrub(self, cred_id: str) -> CredentialRecord:
        """Marks the credential as scrubbed."""
        record = self.get(cred_id)
        if not record:
            raise CredentialError(f"Credential not found: {cred_id}")

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE credentials SET status = ?, strapped_at = NULL WHERE id = ?",
                    (CredentialStatus.SCRUBBED.value, cred_id)
                )
                conn.commit()
            record.status = CredentialStatus.SCRUBBED
            record.strapped_at = None
            return record
        except Exception as e:
            raise CredentialError(f"Failed to update credential status to scrubbed: {e}")

    def nuke(self, cred_id: str) -> CredentialRecord:
        """Marks the credential as permanently destroyed (nuked)."""
        record = self.get(cred_id)
        if not record:
            raise CredentialError(f"Credential not found: {cred_id}")

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE credentials SET status = ?, strapped_at = NULL WHERE id = ?",
                    (CredentialStatus.NUKED.value, cred_id)
                )
                conn.commit()
            record.status = CredentialStatus.NUKED
            record.strapped_at = None
            return record
        except Exception as e:
            raise CredentialError(f"Failed to update credential status to nuked: {e}")
