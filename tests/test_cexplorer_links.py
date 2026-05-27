"""Tests for cexplorer link integration across reports and models."""

from verificador_dpp.modelos import CredencialDPP, PassaporteBateria
from verificador_dpp.relatorio_html import RelatorioHTML
from verificador_dpp.relatorio_reciclagem_html import RelatorioReciclagemHTML


TX_HASH = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"


def _make_cred(**overrides) -> CredencialDPP:
    defaults = dict(
        nome="Product",
        emitente="Corp",
        gtin="1234567890123",
        origem="City",
        fabricado_em="2026-01-01",
        pegada_carbono="1 kg CO2e",
        conteudo_reciclado="5%",
        materiais={},
        referencias={},
        data_hashes={},
    )
    defaults.update(overrides)
    return CredencialDPP(**defaults)


class TestCredencialDPPTxHash:
    def test_tx_hash_default_none(self):
        c = _make_cred()
        assert c.tx_hash is None

    def test_tx_hash_set(self):
        c = _make_cred(tx_hash=TX_HASH)
        assert c.tx_hash == TX_HASH

    def test_tx_hash_backwards_compatible(self):
        """Existing code that doesn't pass tx_hash still works."""
        c = CredencialDPP(
            nome="P", emitente="E", gtin="G", origem="O",
            fabricado_em="2026-01-01", pegada_carbono="1",
            conteudo_reciclado="0%", materiais={}, referencias={},
            data_hashes={},
        )
        assert c.tx_hash is None


class TestRelatorioHTMLCexplorerLinks:
    def test_no_link_without_tx_hash(self):
        rel = RelatorioHTML()
        pb = PassaporteBateria(
            origem=_make_cred(), celula=None, pack=None,
        )
        output = rel.gerar(pb)
        assert "cexplorer.io" not in output

    def test_link_present_with_tx_hash(self):
        rel = RelatorioHTML()
        pb = PassaporteBateria(
            origem=_make_cred(tx_hash=TX_HASH),
            celula=None,
            pack=None,
        )
        output = rel.gerar(pb)
        assert f"https://preprod.cexplorer.io/tx/{TX_HASH}" in output
        assert "card-tx" in output

    def test_link_in_multiple_cards(self):
        rel = RelatorioHTML()
        tx1 = "1111111111111111111111111111111111111111111111111111111111111111"
        tx2 = "2222222222222222222222222222222222222222222222222222222222222222"
        pb = PassaporteBateria(
            origem=_make_cred(tx_hash=tx1),
            celula=_make_cred(tx_hash=tx2),
            pack=None,
        )
        output = rel.gerar(pb)
        assert f"cexplorer.io/tx/{tx1}" in output
        assert f"cexplorer.io/tx/{tx2}" in output


class TestRelatorioReciclagemCexplorerLinks:
    def test_no_card_link_without_tx_hash(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred(
            referencias={"pack_tx": "abc123"},
        ))
        assert '<div class="card-tx">' not in output

    def test_card_link_with_tx_hash(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred(tx_hash=TX_HASH))
        assert f"https://preprod.cexplorer.io/tx/{TX_HASH}" in output
        assert "card-tx" in output

    def test_ref_badges_have_cexplorer_links(self):
        rel = RelatorioReciclagemHTML()
        ref_tx = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
        output = rel.gerar(_make_cred(
            referencias={"pack_tx": ref_tx},
        ))
        assert f"https://preprod.cexplorer.io/tx/{ref_tx}" in output
        assert "<a href=" in output

    def test_ref_badges_link_all_references(self):
        rel = RelatorioReciclagemHTML()
        refs = {
            "pack_tx": "aa" * 32,
            "celula_tx": "bb" * 32,
            "origem_tx": "cc" * 32,
        }
        output = rel.gerar(_make_cred(referencias=refs))
        assert f"cexplorer.io/tx/{'aa' * 32}" in output
        assert f"cexplorer.io/tx/{'bb' * 32}" in output
        assert f"cexplorer.io/tx/{'cc' * 32}" in output
