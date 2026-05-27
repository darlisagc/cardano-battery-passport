"""Tests for relatorio_passaporte.py — report generation."""

from verificador_dpp.modelos import CredencialDPP, PassaporteBateria
from verificador_dpp.relatorio_passaporte import RelatorioPassaporte


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


class TestRelatorioPassaporte:
    def test_report_contains_header(self):
        rel = RelatorioPassaporte()
        pb = PassaporteBateria(origem=None, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "PASSAPORTE VALIDO" in output

    def test_report_contains_sections(self):
        rel = RelatorioPassaporte()
        o = _make_cred(nome="Litio")
        c = _make_cred(nome="Celulas")
        p = _make_cred(nome="Pack")
        pb = PassaporteBateria(origem=o, celula=c, pack=p)
        output = rel.gerar(pb)
        assert "Origem" in output
        assert "células" in output or "Fabricação" in output
        assert "pack" in output.lower() or "Pack" in output

    def test_report_shows_emitente(self):
        rel = RelatorioPassaporte()
        o = _make_cred(emitente="MineraLitio Ltda.")
        pb = PassaporteBateria(origem=o, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "MineraLitio Ltda." in output

    def test_report_shows_materials(self):
        rel = RelatorioPassaporte()
        o = _make_cred(materiais={"niquel": "80%", "cobalto": "10%"})
        pb = PassaporteBateria(origem=o, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "niquel" in output
        assert "80%" in output

    def test_report_handles_none_credentials(self):
        rel = RelatorioPassaporte()
        pb = PassaporteBateria(origem=None, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "credencial ausente" in output

    def test_report_reciclagem_section(self):
        rel = RelatorioPassaporte()
        r = _make_cred(nome="Reciclagem Pack")
        pb = PassaporteBateria(origem=None, celula=None, pack=None, reciclagem=r)
        output = rel.gerar(pb)
        assert "Reciclagem" in output
        assert "Reciclagem Pack" in output

    def test_report_no_reciclagem_when_none(self):
        rel = RelatorioPassaporte()
        pb = PassaporteBateria(origem=None, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "Reciclagem" not in output

    def test_report_footer(self):
        rel = RelatorioPassaporte()
        pb = PassaporteBateria(origem=None, celula=None, pack=None)
        output = rel.gerar(pb)
        assert "verificada on-chain" in output

    def test_report_with_real_payloads(self):
        """Generate a full report using actual payload data."""
        from verificador_dpp._payloads import (
            payload_celula,
            payload_origem,
            payload_pack,
        )
        from verificador_dpp.parser_credencial import ParserCredencial
        from types import SimpleNamespace

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
        rel = RelatorioPassaporte()
        output = rel.gerar(pb)

        assert "MineraLitio Jequitinhonha Ltda." in output
        assert "CellTech Brasil S.A." in output
        assert "PackMontadora SP Ltda." in output
        assert "PASSAPORTE VALIDO" in output
