import json
from dataclasses import replace

import pytest

from cache_service.identity import (
    IdentityCollisionError,
    payload_identity,
    transformation_identity,
)


def test_known_encoding_and_digest_vectors():
    payload = payload_identity(["é", "a\n"], ["😀", ""])
    assert payload.canonical_input == (
        '{"list1":["\\u00e9","a\\n"],"list2":["\\ud83d\\ude00",""],'
        '"version":"uppercase-v1"}'
    )
    assert payload.input_digest.hex() == (
        "8fbf9e67dded6206bf419fa9acfe3ce5f7c1e953b520f532024eff428e8abc03"
    )
    transformation = transformation_identity("é")
    assert transformation.source_digest.hex() == (
        "b98509be7bdc7323c678e7c15ed628c8310ed6031a75b416fd3b6725370f3fff"
    )
    assert transformation.advisory_key == 1669166083383056150
    assert len(payload.input_digest) == len(transformation.source_digest) == 32


@pytest.mark.parametrize("list1,list2", [
    (["b", "a"], ["c", "d"]),  # Order within a list.
    (["c", "d"], ["a", "b"]),  # List boundaries.
    (["a", "a"], ["c", "d"]),  # Duplicate multiplicity.
    ([" a", "b"], ["c", "d"]),
    (["A", "b"], ["c", "d"]),
    (["a,b"], ["c,d"]),  # Delimiters cannot impersonate element boundaries.
])
def test_payload_identity_preserves_request_distinctions(list1, list2):
    original = payload_identity(["a", "b"], ["c", "d"])
    other = payload_identity(list1, list2)
    assert original.canonical_input != other.canonical_input
    assert original.input_digest != other.input_digest


def test_empty_inputs_and_json_special_characters_round_trip():
    assert payload_identity([], []) != payload_identity([""], [""])
    values = ['"\\\n\t', "é", "e\u0301", "😀", "\ud800"]
    identity = payload_identity(values, values)
    decoded = json.loads(identity.canonical_input)
    assert decoded["list1"] == decoded["list2"] == values
    assert transformation_identity("é").source_digest != transformation_identity(
        "e\u0301"
    ).source_digest


@pytest.mark.parametrize("source", ["", "a", " a ", "A", "é", "😀"])
def test_transformation_identity_is_repeatable_and_fits_postgres_bigint(source):
    first = transformation_identity(source)
    assert first == transformation_identity(source)
    assert -(2**63) <= first.advisory_key < 2**63
    first.verify_stored(first.version, source)


def test_version_changes_payload_cache_and_lock_identities():
    first = transformation_identity("a")
    other = transformation_identity("a", version="uppercase-v2")
    assert first.source_digest != other.source_digest
    assert first.advisory_key != other.advisory_key
    assert payload_identity(["a"], ["b"]).input_digest != payload_identity(
        ["a"], ["b"], version="uppercase-v2"
    ).input_digest
    with pytest.raises(IdentityCollisionError):
        first.verify_stored(other.version, other.source)


def test_payload_collision_checks_full_identity_without_exposing_input():
    expected = payload_identity(["private-one"], ["private-two"])
    stored = replace(payload_identity(["different"], ["input"]),
                     input_digest=expected.input_digest)
    assert expected.input_digest == stored.input_digest
    expected.verify_stored(expected.canonical_input)
    with pytest.raises(IdentityCollisionError) as error:
        expected.verify_stored(stored.canonical_input)
    assert str(error.value) == "Stored payload identity does not match"


def test_transformation_digest_collision_still_checks_source():
    expected = transformation_identity("private-source")
    stored = replace(transformation_identity("different"), source_digest=expected.source_digest)
    assert expected.source_digest == stored.source_digest
    with pytest.raises(IdentityCollisionError) as error:
        expected.verify_stored(stored.version, stored.source)
    assert str(error.value) == "Stored transformation identity does not match"


def test_advisory_key_is_never_used_to_verify_cached_identity(monkeypatch):
    # Force only lock hashes to collide; full database lookup digests remain distinct.
    first = transformation_identity("one")
    second = transformation_identity("two")

    class LockHash:
        def digest(self):
            return b"\xff" * 32

    monkeypatch.setattr("cache_service.identity.sha256", lambda value: LockHash())
    assert first.advisory_key == second.advisory_key == -1
    assert first.source_digest != second.source_digest
    first.verify_stored(first.version, "one")
    second.verify_stored(second.version, "two")
    with pytest.raises(IdentityCollisionError):
        first.verify_stored(second.version, second.source)
