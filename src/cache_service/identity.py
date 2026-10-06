"""Versioned identities for validated inputs and immutable stored records."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256

TRANSFORMER_VERSION = "uppercase-v1"
_LOCK_NAMESPACE = b"cache-service:transformation-lock:v1\x00"


class IdentityCollisionError(RuntimeError):
    """A digest lookup returned a record belonging to a different input."""


def _canonical_json(value: dict[str, object]) -> str:
    # ASCII escapes also preserve lone surrogate code points without UTF-8 encoding errors.
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class PayloadIdentity:
    canonical_input: str
    input_digest: bytes

    def verify_stored(self, canonical_input: str) -> None:
        """Check the full stored identity before reusing its identifier."""
        if canonical_input != self.canonical_input:
            raise IdentityCollisionError("Stored payload identity does not match")


@dataclass(frozen=True)
class TransformationIdentity:
    version: str
    source: str
    source_digest: bytes

    @property
    def advisory_key(self) -> int:
        """Return a PostgreSQL bigint key in the transformation lock namespace."""
        lock_digest = sha256(_LOCK_NAMESPACE + self.source_digest).digest()
        return int.from_bytes(lock_digest[:8], byteorder="big", signed=True)

    def verify_stored(self, version: str, source: str) -> None:
        """Check both retained fields before reusing a transformation result."""
        if (version, source) != (self.version, self.source):
            raise IdentityCollisionError("Stored transformation identity does not match")


def payload_identity(
    list1: Sequence[str], list2: Sequence[str], *, version: str = TRANSFORMER_VERSION
) -> PayloadIdentity:
    """Encode validated lists without changing their content, order, or boundaries."""
    canonical_input = _canonical_json(
        {"version": version, "list1": list(list1), "list2": list(list2)}
    )
    return PayloadIdentity(canonical_input, sha256(canonical_input.encode("utf-8")).digest())


def transformation_identity(
    source: str, *, version: str = TRANSFORMER_VERSION
) -> TransformationIdentity:
    canonical_input = _canonical_json({"version": version, "source": source})
    return TransformationIdentity(
        version, source, sha256(canonical_input.encode("utf-8")).digest()
    )
