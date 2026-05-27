"""Tests for relatorio_html.py — HTML report generation."""

from verificador_dpp.modelos import CredencialDPP, PassaporteBateria
from verificador_dpp.relatorio_html import RelatorioHTML


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


class TestRelatorioHTML:
    def test_html_contains_header(self):
        rel = RelatorioHTML()
        pb = PassaporteBateria(origem=None, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "Passaporte Digital de Produto" in output

    def test_html_contains_subtitle(self):
        rel = RelatorioHTML()
        pb = PassaporteBateria(origem=None, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "Jequitinhonha" in output

    def test_html_contains_sections(self):
        rel = RelatorioHTML()
        o = _make_cred(nome="Litio")
        c = _make_cred(nome="Celulas")
        p = _make_cred(nome="Pack")
        pb = PassaporteBateria(origem=o, celula=c, pack=p)
        output = rel.gerar(pb)
        assert "Origem" in output
        assert "lula" in output or "Fabrica" in output
        assert "pack" in output.lower() or "Pack" in output

    def test_html_shows_emitente(self):
        rel = RelatorioHTML()
        o = _make_cred(emitente="MineraLitio Ltda.")
        pb = PassaporteBateria(origem=o, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "MineraLitio Ltda." in output

    def test_html_shows_materials(self):
        rel = RelatorioHTML()
        o = _make_cred(materiais={"niquel": "80%", "cobalto": "10%"})
        pb = PassaporteBateria(origem=o, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "niquel" in output
        assert "80%" in output

    def test_html_handles_none_credentials(self):
        rel = RelatorioHTML()
        pb = PassaporteBateria(origem=None, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "credencial ausente" in output

    def test_html_footer(self):
        rel = RelatorioHTML()
        pb = PassaporteBateria(origem=None, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "verificada on-chain" in output

    def test_html_verified_banner(self):
        rel = RelatorioHTML()
        pb = PassaporteBateria(origem=None, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "Verificado na Blockchain Cardano" in output
        assert "verified-badge" in output

    def test_html_is_self_contained(self):
        rel = RelatorioHTML()
        pb = PassaporteBateria(origem=None, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "<!DOCTYPE html>" in output
        assert "<style>" in output
        assert "</html>" in output

    def test_html_supply_chain_flow(self):
        rel = RelatorioHTML()
        pb = PassaporteBateria(origem=None, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "flow-step origem" in output
        assert "flow-step celula" in output
        assert "flow-step pack" in output
        assert "flow-step reciclagem" not in output

    def test_html_reciclagem_card(self):
        rel = RelatorioHTML()
        r = _make_cred(nome="Reciclagem Pack")
        pb = PassaporteBateria(
            origem=None, celula=None, pack=None, reciclagem=r,
        )
        output = rel.gerar(pb)
        assert "Reciclagem" in output
        assert "flow-step reciclagem" in output
        assert "Reciclagem Pack" in output

    def test_html_escapes_special_characters(self):
        rel = RelatorioHTML()
        o = _make_cred(emitente="Corp <script>alert(1)</script>")
        pb = PassaporteBateria(origem=o, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "<script>" not in output
        assert "&lt;script&gt;" in output

    def test_html_badge_metadata(self):
        rel = RelatorioHTML()
        o = _make_cred(metodo_emissao="metadata")
        pb = PassaporteBateria(origem=o, celula=None, pack=None)
        output = rel.gerar(pb)
        assert 'emission-badge metadata' in output
        assert "Metadata" in output

    def test_html_badge_uverify(self):
        rel = RelatorioHTML()
        o = _make_cred(metodo_emissao="uverify")
        pb = PassaporteBateria(origem=o, celula=None, pack=None)
        output = rel.gerar(pb)
        assert 'emission-badge uverify' in output
        assert "UVerify" in output

    def test_html_no_badge_when_none(self):
        rel = RelatorioHTML()
        o = _make_cred()
        pb = PassaporteBateria(origem=o, celula=None, pack=None)
        output = rel.gerar(pb)
        assert '<span class="emission-badge' not in output

    def test_html_with_real_payloads(self):
        """Generate a full HTML report using actual payload data."""
        from types import SimpleNamespace

        from verificador_dpp._payloads import (
            payload_celula,
            payload_origem,
            payload_pack,
        )
        from verificador_dpp.parser_credencial import ParserCredencial

        parser = ParserCredencial()
        env = {"ATOR1_TX": "tx1", "ATOR2_TX": "tx2"}

        p_o, _, _ = payload_origem()
        p_c, _, _ = payload_celula(env)
        p_p, _, _ = payload_pack(env)

        cred_o = parser.extrair_credencial(
            [SimpleNamespace(label="1990", json_metadata=p_o)]
        )
        cred_c = parser.extrair_credencial(
            [SimpleNamespace(label="1990", json_metadata=p_c)]
        )
        cred_p = parser.extrair_credencial(
            [SimpleNamespace(label="1990", json_metadata=p_p)]
        )

        pb = PassaporteBateria(origem=cred_o, celula=cred_c, pack=cred_p)
        rel = RelatorioHTML()
        output = rel.gerar(pb)

        assert "MineraLitio Jequitinhonha Ltda." in output
        assert "CellTech Brasil S.A." in output
        assert "PackMontadora SP Ltda." in output
        assert "Passaporte Digital de Produto" in output
        assert "<!DOCTYPE html>" in output
