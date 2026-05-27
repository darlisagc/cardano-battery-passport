"""Tests for parser_credencial.py — metadata parsing and CredencialDPP conversion."""

from types import SimpleNamespace

import pytest

from verificador_dpp.modelos import CredencialDPP
from verificador_dpp.parser_credencial import ParserCredencial


@pytest.fixture
def parser():
    return ParserCredencial()


def _make_entry(label: int, payload: dict) -> SimpleNamespace:
    """Simulate a Blockfrost metadata entry (Namespace with json_metadata)."""
    return SimpleNamespace(label=str(label), json_metadata=payload)


# ── Basic parsing ────────────────────────────────────────────────────


class TestExtrairCredencial:
    def test_parses_simple_payload(self, parser):
        payload = {
            "uverify_template_id": "digitalProductPassport",
            "uverify_update_policy": "restricted",
            "name": "Test Product",
            "issuer": "Test Corp",
            "gtin": "1234567890123",
            "uv_url_serial": "abc123",
            "origin": "Test City",
            "manufactured": "2026-01-01",
            "carbon_footprint": "1 kg CO2e",
            "recycled_content": "5%",
        }
        entry = _make_entry(1990, payload)
        cred = parser.extrair_credencial([entry])

        assert isinstance(cred, CredencialDPP)
        assert cred.nome == "Test Product"
        assert cred.emitente == "Test Corp"
        assert cred.gtin == "1234567890123"
        assert cred.origem == "Test City"
        assert cred.fabricado_em == "2026-01-01"
        assert cred.pegada_carbono == "1 kg CO2e"
        assert cred.conteudo_reciclado == "5%"
        assert cred.metodo_emissao == "metadata"

    def test_raises_on_empty_metadata(self, parser):
        with pytest.raises(ValueError, match="nao possui metadados"):
            parser.extrair_credencial([])

    def test_raises_on_missing_template_id(self, parser):
        entry = _make_entry(1990, {"name": "something", "issuer": "corp"})
        with pytest.raises(ValueError, match="uverify_template_id"):
            parser.extrair_credencial([entry])

    def test_raises_on_wrong_template_id(self, parser):
        entry = _make_entry(
            1990,
            {"uverify_template_id": "wrongTemplate", "name": "x"},
        )
        with pytest.raises(ValueError, match="Template desconhecido"):
            parser.extrair_credencial([entry])


# ── Material fields ──────────────────────────────────────────────────


class TestMaterialParsing:
    def test_extracts_mat_fields(self, parser):
        payload = {
            "uverify_template_id": "digitalProductPassport",
            "name": "P",
            "issuer": "I",
            "mat_niquel": "80%",
            "mat_cobalto": "10%",
        }
        cred = parser.extrair_credencial([_make_entry(1990, payload)])
        assert cred.materiais == {"niquel": "80%", "cobalto": "10%"}

    def test_no_materials_produces_empty_dict(self, parser):
        payload = {
            "uverify_template_id": "digitalProductPassport",
            "name": "P",
            "issuer": "I",
        }
        cred = parser.extrair_credencial([_make_entry(1990, payload)])
        assert cred.materiais == {}


# ── Credential references ───────────────────────────────────────────


class TestReferenceParsing:
    def test_extracts_credential_tx_refs(self, parser):
        payload = {
            "uverify_template_id": "digitalProductPassport",
            "name": "P",
            "issuer": "I",
            "ref_origem_tx": "tx_hash_abc",
            "ref_celula_tx": "tx_hash_def",
        }
        cred = parser.extrair_credencial([_make_entry(1990, payload)])
        assert cred.referencias == {
            "origem_tx": "tx_hash_abc",
            "celula_tx": "tx_hash_def",
        }

    def test_extracts_data_hash_refs(self, parser):
        payload = {
            "uverify_template_id": "digitalProductPassport",
            "name": "P",
            "issuer": "I",
            "ref_origem_data_hash": "hash_abc",
            "ref_celula_data_hash": "hash_def",
        }
        cred = parser.extrair_credencial([_make_entry(1990, payload)])
        assert cred.data_hashes == {
            "origem_data_hash": "hash_abc",
            "celula_data_hash": "hash_def",
        }

    def test_cert_labels_not_treated_as_refs(self, parser):
        """cert_* fields (actual certifications) should NOT be in
        referencias or data_hashes — only ref_* fields are references."""
        payload = {
            "uverify_template_id": "digitalProductPassport",
            "name": "P",
            "issuer": "I",
            "cert_esg_iso14001": "ISO 14001:2015",
            "cert_licenca_ambiental": "SUPRAM-JQT-LI-042-2024",
        }
        cred = parser.extrair_credencial([_make_entry(1990, payload)])
        assert cred.referencias == {}
        assert cred.data_hashes == {}


# ── Namespace normalization ──────────────────────────────────────────


class TestNamespaceNormalization:
    def test_nested_namespace(self, parser):
        """Blockfrost may return nested Namespace objects."""
        inner = SimpleNamespace(
            uverify_template_id="digitalProductPassport",
            name="Nested",
            issuer="Corp",
        )
        entry = SimpleNamespace(
            label="1990", json_metadata=SimpleNamespace(data=inner)
        )
        cred = parser.extrair_credencial([entry])
        assert cred.nome == "Nested"

    def test_already_dict(self, parser):
        """If metadata is already a dict, it should still work."""
        payload = {
            "uverify_template_id": "digitalProductPassport",
            "name": "Dict",
            "issuer": "Corp",
        }
        entry = _make_entry(1990, payload)
        cred = parser.extrair_credencial([entry])
        assert cred.nome == "Dict"


# ── Multiple labels ──────────────────────────────────────────────────


class TestMultipleLabels:
    def test_finds_credential_across_labels(self, parser):
        """Should find the credential even if it's not in the first label."""
        noise = _make_entry(100, {"random": "data"})
        real = _make_entry(
            1990,
            {
                "uverify_template_id": "digitalProductPassport",
                "name": "Found",
                "issuer": "Corp",
            },
        )
        cred = parser.extrair_credencial([noise, real])
        assert cred.nome == "Found"


# ── Integration: parse real payload from _payloads ───────────────────


class TestParseRealPayloads:
    """Parse the actual payloads from _payloads.py to confirm compatibility."""

    def test_parse_payload_origem(self, parser):
        from verificador_dpp._payloads import payload_origem

        payload, serial, gtin = payload_origem()
        entry = _make_entry(1990, payload)
        cred = parser.extrair_credencial([entry])

        assert cred.nome == "Lote Litio Jequitinhonha 2026-05"
        assert cred.emitente == "MineraLitio Jequitinhonha Ltda."
        assert cred.gtin == gtin
        assert cred.referencias == {}
        assert "litio_carbonato" in cred.materiais

    def test_parse_payload_celula(self, parser):
        from verificador_dpp._payloads import payload_celula

        env = {"ATOR1_TX": "fake_tx_1"}
        payload, serial, gtin = payload_celula(env)
        entry = _make_entry(1990, payload)
        cred = parser.extrair_credencial([entry])

        assert cred.nome == "Celulas NMC 811 - Lote BA-2026-05-000000"
        assert "origem_tx" in cred.referencias
        assert "origem_data_hash" in cred.data_hashes

    def test_parse_payload_pack(self, parser):
        from verificador_dpp._payloads import payload_pack

        env = {"ATOR2_TX": "fake_tx_2"}
        payload, serial, gtin = payload_pack(env)
        entry = _make_entry(1990, payload)
        cred = parser.extrair_credencial([entry])

        assert cred.nome == "Pack EV 75kWh - SP-2026-05-000000"
        assert "celula_tx" in cred.referencias
        assert "celula_data_hash" in cred.data_hashes

    def test_parse_payload_reciclagem(self, parser):
        from verificador_dpp._payloads import payload_reciclagem

        env = {"ATOR1_TX": "t1", "ATOR2_TX": "t2", "ATOR3_TX": "t3"}
        payload, serial, gtin = payload_reciclagem(env)
        entry = _make_entry(1990, payload)
        cred = parser.extrair_credencial([entry])

        assert cred.nome == "Reciclagem Pack 75kWh - SR-2031-09-000000"
        assert len(cred.referencias) == 3
        assert len(cred.data_hashes) == 3

    def test_update_policy_does_not_pollute_references(self, parser):
        """uverify_update_policy should not appear in materiais, referencias,
        or data_hashes."""
        from verificador_dpp._payloads import payload_origem

        payload, _, _ = payload_origem()
        entry = _make_entry(1990, payload)
        cred = parser.extrair_credencial([entry])

        all_parsed_keys = set(cred.materiais.keys()) | set(
            cred.referencias.keys()
        ) | set(cred.data_hashes.keys())
        assert "uverify_update_policy" not in all_parsed_keys
