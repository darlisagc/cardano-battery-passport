"""Tests for _payloads.py — payload structure, field correctness, and chaining."""

from hashlib import sha256

import pytest

from verificador_dpp._payloads import (
    ATORES,
    PROXIMO_ATOR_ENV,
    data_hash,
    payload_celula,
    payload_origem,
    payload_pack,
    payload_reciclagem,
)

# Simulated env with all ATOR*_TX filled.
FAKE_ENV = {
    "ATOR1_TX": "aaa111",
    "ATOR2_TX": "bbb222",
    "ATOR3_TX": "ccc333",
}

# All payload functions and their names.
ALL_PAYLOADS = [
    ("origem", lambda: payload_origem()),
    ("celula", lambda: payload_celula(FAKE_ENV)),
    ("pack", lambda: payload_pack(FAKE_ENV)),
    ("reciclagem", lambda: payload_reciclagem(FAKE_ENV)),
]


# ── data_hash and _hash_serial ─────────────────────────────────────


class TestDataHash:
    def test_deterministic(self):
        h1 = data_hash("7891234560013", "ML-JQT-2026-03-042")
        h2 = data_hash("7891234560013", "ML-JQT-2026-03-042")
        assert h1 == h2

    def test_known_value(self):
        expected = sha256(
            ("7891234560013" + "ML-JQT-2026-03-042").encode("utf-8")
        ).hexdigest()
        assert data_hash("7891234560013", "ML-JQT-2026-03-042") == expected

    def test_different_inputs_differ(self):
        assert data_hash("A", "B") != data_hash("B", "A")

    def test_output_is_64_hex_chars(self):
        h = data_hash("gtin", "serial")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ── Common payload structure ────────────────────────────────────────


class TestPayloadStructure:
    """Every payload must satisfy the UVerify SDK contract."""

    @pytest.mark.parametrize("name,fn", ALL_PAYLOADS)
    def test_returns_tuple_of_three(self, name, fn):
        result = fn()
        assert isinstance(result, tuple)
        assert len(result) == 3

    @pytest.mark.parametrize("name,fn", ALL_PAYLOADS)
    def test_payload_is_dict(self, name, fn):
        payload, _, _ = fn()
        assert isinstance(payload, dict)

    @pytest.mark.parametrize("name,fn", ALL_PAYLOADS)
    def test_serial_and_gtin_are_strings(self, name, fn):
        _, serial, gtin = fn()
        assert isinstance(serial, str) and serial
        assert isinstance(gtin, str) and gtin

    @pytest.mark.parametrize("name,fn", ALL_PAYLOADS)
    def test_all_values_are_strings(self, name, fn):
        """UVerify SDK requires Dict[str, str] for metadata."""
        payload, _, _ = fn()
        for key, val in payload.items():
            assert isinstance(val, str), (
                f"Payload '{name}': field '{key}' has type {type(val).__name__}, "
                f"expected str"
            )

    @pytest.mark.parametrize("name,fn", ALL_PAYLOADS)
    def test_no_value_exceeds_64_bytes(self, name, fn):
        """Cardano metadata string limit is 64 bytes."""
        payload, _, _ = fn()
        for key, val in payload.items():
            assert len(val.encode("utf-8")) <= 64, (
                f"Payload '{name}': field '{key}' value is "
                f"{len(val.encode('utf-8'))} bytes (max 64)"
            )

    @pytest.mark.parametrize("name,fn", ALL_PAYLOADS)
    def test_required_fields_present(self, name, fn):
        """UVerify template requires these fields."""
        payload, _, _ = fn()
        required = [
            "uverify_template_id",
            "name",
            "issuer",
            "gtin",
            "uv_url_serial",
        ]
        for field in required:
            assert field in payload, (
                f"Payload '{name}': missing required field '{field}'"
            )

    @pytest.mark.parametrize("name,fn", ALL_PAYLOADS)
    def test_template_id_is_correct(self, name, fn):
        payload, _, _ = fn()
        assert payload["uverify_template_id"] == "digitalProductPassport"


# ── uverify_update_policy (new field) ──────────────────────────────


class TestUpdatePolicy:
    """Verify uverify_update_policy is present and correct in all payloads."""

    @pytest.mark.parametrize("name,fn", ALL_PAYLOADS)
    def test_update_policy_present(self, name, fn):
        payload, _, _ = fn()
        assert "uverify_update_policy" in payload, (
            f"Payload '{name}': missing uverify_update_policy"
        )

    @pytest.mark.parametrize("name,fn", ALL_PAYLOADS)
    def test_update_policy_value_is_restricted(self, name, fn):
        payload, _, _ = fn()
        assert payload["uverify_update_policy"] == "restricted", (
            f"Payload '{name}': uverify_update_policy should be 'restricted', "
            f"got '{payload.get('uverify_update_policy')}'"
        )


# ── uv_url_serial consistency ──────────────────────────────────────


class TestUvUrlSerial:
    @pytest.mark.parametrize("name,fn", ALL_PAYLOADS)
    def test_uv_url_serial_matches_sha256_of_serial(self, name, fn):
        payload, serial, _ = fn()
        expected_hash = sha256(serial.encode("utf-8")).hexdigest()
        assert payload["uv_url_serial"] == expected_hash


# ── Payload-specific: origem ────────────────────────────────────────


class TestPayloadOrigem:
    def test_no_credential_references(self):
        """Ator 1 should NOT reference any previous actor."""
        payload, _, _ = payload_origem()
        cred_refs = [k for k in payload if k.endswith("_credential_tx")]
        assert cred_refs == [], f"Unexpected credential refs: {cred_refs}"

    def test_no_data_hash_refs(self):
        payload, _, _ = payload_origem()
        dh_refs = [k for k in payload if k.endswith("_data_hash")]
        assert dh_refs == []

    def test_gtin_and_serial(self):
        _, serial, gtin = payload_origem()
        assert gtin == "7891234560013"
        assert serial == "ML-JQT-2026-03-042"

    def test_accepts_none_env(self):
        """payload_origem can be called without env."""
        payload, serial, gtin = payload_origem(None)
        assert payload["name"] == "Lote Litio Jequitinhonha 2026-03"

    def test_has_material_fields(self):
        payload, _, _ = payload_origem()
        mat_fields = [k for k in payload if k.startswith("mat_")]
        assert len(mat_fields) >= 1


# ── Payload-specific: celula ────────────────────────────────────────


class TestPayloadCelula:
    def test_references_ator1(self):
        payload, _, _ = payload_celula(FAKE_ENV)
        assert payload["cert_origem_credential_tx"] == "aaa111"

    def test_data_hash_for_ator1(self):
        payload, _, _ = payload_celula(FAKE_ENV)
        expected = data_hash("7891234560013", "ML-JQT-2026-03-042")
        assert payload["cert_origem_data_hash"] == expected

    def test_gtin_and_serial(self):
        _, serial, gtin = payload_celula(FAKE_ENV)
        assert gtin == "7891234560020"
        assert serial == "CT-BA-2026-04-008"

    def test_fails_without_ator1_tx(self):
        with pytest.raises(SystemExit):
            payload_celula({})


# ── Payload-specific: pack ──────────────────────────────────────────


class TestPayloadPack:
    def test_references_ator2(self):
        payload, _, _ = payload_pack(FAKE_ENV)
        assert payload["cert_celula_credential_tx"] == "bbb222"

    def test_data_hash_for_ator2(self):
        payload, _, _ = payload_pack(FAKE_ENV)
        expected = data_hash("7891234560020", "CT-BA-2026-04-008")
        assert payload["cert_celula_data_hash"] == expected

    def test_gtin_and_serial(self):
        _, serial, gtin = payload_pack(FAKE_ENV)
        assert gtin == "7891234560037"
        assert serial == "PM-SP-2026-04-155"

    def test_fails_without_ator2_tx(self):
        with pytest.raises(SystemExit):
            payload_pack({"ATOR1_TX": "aaa111"})


# ── Payload-specific: reciclagem ────────────────────────────────────


class TestPayloadReciclagem:
    def test_references_all_three_actors(self):
        payload, _, _ = payload_reciclagem(FAKE_ENV)
        assert payload["cert_pack_credential_tx"] == "ccc333"
        assert payload["cert_celula_credential_tx"] == "bbb222"
        assert payload["cert_origem_credential_tx"] == "aaa111"

    def test_data_hashes_for_all_three(self):
        payload, _, _ = payload_reciclagem(FAKE_ENV)
        assert payload["cert_pack_data_hash"] == data_hash(
            "7891234560037", "PM-SP-2026-04-155"
        )
        assert payload["cert_celula_data_hash"] == data_hash(
            "7891234560020", "CT-BA-2026-04-008"
        )
        assert payload["cert_origem_data_hash"] == data_hash(
            "7891234560013", "ML-JQT-2026-03-042"
        )

    def test_gtin_and_serial(self):
        _, serial, gtin = payload_reciclagem(FAKE_ENV)
        assert gtin == "7891234560044"
        assert serial == "RL-SR-2031-08-001"

    def test_fails_without_any_ator_tx(self):
        with pytest.raises(SystemExit):
            payload_reciclagem({})

    def test_fails_without_ator3_tx(self):
        with pytest.raises(SystemExit):
            payload_reciclagem({"ATOR1_TX": "a", "ATOR2_TX": "b"})


# ── ATORES registry ────────────────────────────────────────────────


class TestAtoresRegistry:
    def test_has_all_four_actors(self):
        assert set(ATORES.keys()) == {"origem", "celula", "pack", "reciclagem"}

    def test_proximo_ator_env_keys_match(self):
        assert set(PROXIMO_ATOR_ENV.keys()) == set(ATORES.keys())

    def test_proximo_ator_env_values(self):
        assert PROXIMO_ATOR_ENV["origem"] == "ATOR1_TX"
        assert PROXIMO_ATOR_ENV["celula"] == "ATOR2_TX"
        assert PROXIMO_ATOR_ENV["pack"] == "ATOR3_TX"
        assert PROXIMO_ATOR_ENV["reciclagem"] == "ATOR4_TX"

    def test_atores_callables_work(self):
        """All ATORES entries are callable and produce valid payloads."""
        for name, fn in ATORES.items():
            if name == "origem":
                result = fn(None)
            else:
                result = fn(FAKE_ENV)
            assert isinstance(result, tuple)
            assert len(result) == 3


# ── Cross-payload consistency ───────────────────────────────────────


class TestChainConsistency:
    """Verify that cross-references between payloads are consistent."""

    def test_celula_data_hash_matches_origem(self):
        """celula's cert_origem_data_hash must match data_hash(gtin, serial)
        of the actual origem payload."""
        _, serial_o, gtin_o = payload_origem()
        payload_c, _, _ = payload_celula(FAKE_ENV)
        assert payload_c["cert_origem_data_hash"] == data_hash(gtin_o, serial_o)

    def test_pack_data_hash_matches_celula(self):
        _, serial_c, gtin_c = payload_celula(FAKE_ENV)
        payload_p, _, _ = payload_pack(FAKE_ENV)
        assert payload_p["cert_celula_data_hash"] == data_hash(gtin_c, serial_c)

    def test_reciclagem_data_hashes_match_all(self):
        _, serial_o, gtin_o = payload_origem()
        _, serial_c, gtin_c = payload_celula(FAKE_ENV)
        _, serial_p, gtin_p = payload_pack(FAKE_ENV)
        payload_r, _, _ = payload_reciclagem(FAKE_ENV)

        assert payload_r["cert_origem_data_hash"] == data_hash(gtin_o, serial_o)
        assert payload_r["cert_celula_data_hash"] == data_hash(gtin_c, serial_c)
        assert payload_r["cert_pack_data_hash"] == data_hash(gtin_p, serial_p)

    def test_all_gtins_are_unique(self):
        gtins = set()
        for name, fn in ALL_PAYLOADS:
            _, _, gtin = fn()
            assert gtin not in gtins, f"Duplicate GTIN {gtin} in payload '{name}'"
            gtins.add(gtin)

    def test_all_serials_are_unique(self):
        serials = set()
        for name, fn in ALL_PAYLOADS:
            _, serial, _ = fn()
            assert serial not in serials, f"Duplicate serial {serial} in '{name}'"
            serials.add(serial)
