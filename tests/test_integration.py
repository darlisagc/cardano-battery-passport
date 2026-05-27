"""Integration tests — end-to-end payload → parse → report pipeline.

These tests simulate the full workshop flow without hitting the blockchain:
  1. Generate payloads for all 4 actors
  2. Parse them as if they came from Blockfrost metadata
  3. Verify cross-references are consistent
  4. Generate a report
"""

from hashlib import sha256
from types import SimpleNamespace

import pytest

from verificador_dpp._payloads import (
    data_hash,
    payload_celula,
    payload_origem,
    payload_pack,
    payload_reciclagem,
)
from verificador_dpp.modelos import PassaporteBateria
from verificador_dpp.parser_credencial import ParserCredencial
from verificador_dpp.relatorio_passaporte import RelatorioPassaporte


FAKE_ENV = {
    "ATOR1_TX": "aaaa1111",
    "ATOR2_TX": "bbbb2222",
    "ATOR3_TX": "cccc3333",
}


def _parse(parser, payload):
    entry = SimpleNamespace(label="1990", json_metadata=payload)
    return parser.extrair_credencial([entry])


class TestFullPipeline:
    """Simulate the complete workshop flow."""

    @pytest.fixture
    def parser(self):
        return ParserCredencial()

    @pytest.fixture
    def all_payloads(self):
        p_o, s_o, g_o = payload_origem()
        p_c, s_c, g_c = payload_celula(FAKE_ENV)
        p_p, s_p, g_p = payload_pack(FAKE_ENV)
        p_r, s_r, g_r = payload_reciclagem(FAKE_ENV)
        return {
            "origem": (p_o, s_o, g_o),
            "celula": (p_c, s_c, g_c),
            "pack": (p_p, s_p, g_p),
            "reciclagem": (p_r, s_r, g_r),
        }

    def test_all_payloads_parseable(self, parser, all_payloads):
        """Every payload should parse without error."""
        for name, (payload, serial, gtin) in all_payloads.items():
            cred = _parse(parser, payload)
            assert cred.nome is not None, f"{name}: nome should not be None"
            assert cred.emitente is not None, f"{name}: emitente should not be None"

    def test_chain_walk_pack_to_origem(self, parser, all_payloads):
        """Simulate the verifier walking from pack → celula → origem."""
        # Parse pack
        pack_payload, _, _ = all_payloads["pack"]
        cred_pack = _parse(parser, pack_payload)

        # Pack should reference celula
        assert "celula_tx" in cred_pack.referencias
        assert cred_pack.referencias["celula_tx"] == FAKE_ENV["ATOR2_TX"]

        # Pack should have celula data_hash
        assert "celula_data_hash" in cred_pack.data_hashes
        _, serial_c, gtin_c = all_payloads["celula"]
        assert cred_pack.data_hashes["celula_data_hash"] == data_hash(gtin_c, serial_c)

        # Parse celula
        cel_payload, _, _ = all_payloads["celula"]
        cred_cel = _parse(parser, cel_payload)

        # Celula should reference origem
        assert "origem_tx" in cred_cel.referencias
        assert cred_cel.referencias["origem_tx"] == FAKE_ENV["ATOR1_TX"]

        # Parse origem
        orig_payload, _, _ = all_payloads["origem"]
        cred_orig = _parse(parser, orig_payload)

        # Origem should have no references
        assert cred_orig.referencias == {}

    def test_reciclagem_references_all(self, parser, all_payloads):
        """Reciclagem should reference all three previous actors."""
        rec_payload, _, _ = all_payloads["reciclagem"]
        cred_rec = _parse(parser, rec_payload)

        assert len(cred_rec.referencias) == 3
        assert cred_rec.referencias["pack_tx"] == FAKE_ENV["ATOR3_TX"]
        assert cred_rec.referencias["celula_tx"] == FAKE_ENV["ATOR2_TX"]
        assert cred_rec.referencias["origem_tx"] == FAKE_ENV["ATOR1_TX"]

        assert len(cred_rec.data_hashes) == 3

    def test_reciclagem_chain_walk(self, parser, all_payloads):
        """Simulate the verifier auto-detecting reciclagem entry point
        and walking: reciclagem → pack → celula → origem."""
        rec_payload, _, _ = all_payloads["reciclagem"]
        cred_rec = _parse(parser, rec_payload)

        # Reciclagem should have ref_pack_tx — triggers auto-detect
        assert "pack_tx" in cred_rec.referencias
        assert cred_rec.referencias["pack_tx"] == FAKE_ENV["ATOR3_TX"]

        # Follow to pack
        pack_payload, _, _ = all_payloads["pack"]
        cred_pack = _parse(parser, pack_payload)
        assert "celula_tx" in cred_pack.referencias

        # Follow to celula
        cel_payload, _, _ = all_payloads["celula"]
        cred_cel = _parse(parser, cel_payload)
        assert "origem_tx" in cred_cel.referencias

        # Follow to origem
        orig_payload, _, _ = all_payloads["origem"]
        cred_orig = _parse(parser, orig_payload)
        assert cred_orig.referencias == {}

        # Build full passaporte with reciclagem
        passaporte = PassaporteBateria(
            origem=cred_orig, celula=cred_cel, pack=cred_pack,
            reciclagem=cred_rec,
        )
        assert passaporte.reciclagem is not None
        assert passaporte.reciclagem.nome is not None

    def test_full_report_generation(self, parser, all_payloads):
        """Generate a complete report from the parsed chain."""
        cred_o = _parse(parser, all_payloads["origem"][0])
        cred_c = _parse(parser, all_payloads["celula"][0])
        cred_p = _parse(parser, all_payloads["pack"][0])

        passaporte = PassaporteBateria(
            origem=cred_o, celula=cred_c, pack=cred_p
        )
        rel = RelatorioPassaporte()
        output = rel.gerar(passaporte)

        # Header
        assert "PASSAPORTE VALIDO" in output

        # All actors present
        assert "MineraLitio" in output
        assert "CellTech" in output
        assert "PackMontadora" in output

        # Footer
        assert "verificada on-chain" in output

    def test_all_payloads_have_update_policy(self, all_payloads):
        """Verify uverify_update_policy in all payloads (integration check)."""
        for name, (payload, _, _) in all_payloads.items():
            assert payload.get("uverify_update_policy") == "restricted", (
                f"Payload '{name}' missing or wrong uverify_update_policy"
            )

    def test_mixed_chain_scenario(self, parser, all_payloads):
        """Simulate the recommended mixed-emission flow:
        Ator 1+2 via Option A, Ator 3 via Option B, Ator 4 via Option C.
        All should parse identically since they use the same payload structure."""
        for name, (payload, serial, gtin) in all_payloads.items():
            cred = _parse(parser, payload)
            assert cred.gtin == gtin
            # uv_url_serial should match sha256 of serial
            expected_serial_hash = sha256(serial.encode("utf-8")).hexdigest()
            assert payload["uv_url_serial"] == expected_serial_hash


class TestDataHashConsistency:
    """Verify that data_hash references match the actual products."""

    def test_celula_points_to_real_origem(self):
        _, serial_o, gtin_o = payload_origem()
        payload_c, _, _ = payload_celula(FAKE_ENV)
        expected = sha256((gtin_o + serial_o).encode("utf-8")).hexdigest()
        assert payload_c["ref_origem_data_hash"] == expected

    def test_pack_points_to_real_celula(self):
        _, serial_c, gtin_c = payload_celula(FAKE_ENV)
        payload_p, _, _ = payload_pack(FAKE_ENV)
        expected = sha256((gtin_c + serial_c).encode("utf-8")).hexdigest()
        assert payload_p["ref_celula_data_hash"] == expected

    def test_reciclagem_points_to_all_real_actors(self):
        _, serial_o, gtin_o = payload_origem()
        _, serial_c, gtin_c = payload_celula(FAKE_ENV)
        _, serial_p, gtin_p = payload_pack(FAKE_ENV)
        payload_r, _, _ = payload_reciclagem(FAKE_ENV)

        assert payload_r["ref_origem_data_hash"] == sha256(
            (gtin_o + serial_o).encode("utf-8")
        ).hexdigest()
        assert payload_r["ref_celula_data_hash"] == sha256(
            (gtin_c + serial_c).encode("utf-8")
        ).hexdigest()
        assert payload_r["ref_pack_data_hash"] == sha256(
            (gtin_p + serial_p).encode("utf-8")
        ).hexdigest()
