"""Tests for relatorio_reciclagem_html.py — recycling HTML report."""

from verificador_dpp.modelos import CredencialDPP
from verificador_dpp.relatorio_reciclagem_html import RelatorioReciclagemHTML


def _make_cred(**overrides) -> CredencialDPP:
    defaults = dict(
        nome="Reciclagem Pack 75kWh",
        emitente="RecicLar Sorocaba S.A.",
        gtin="7891234560044",
        origem="Sorocaba, SP, BR",
        fabricado_em="2031-08-17",
        pegada_carbono=None,
        conteudo_reciclado="N/A (processo de reciclagem)",
        materiais={
            "litio_recuperado": "3.8 kg",
            "niquel_recuperado": "38 kg",
            "cobalto_recuperado": "4.6 kg",
        },
        referencias={
            "pack_tx": "abc123def456",
            "celula_tx": "def789abc012",
            "origem_tx": "ghi345jkl678",
        },
        data_hashes={
            "pack_data_hash": "hash_pack",
            "celula_data_hash": "hash_celula",
            "origem_data_hash": "hash_origem",
        },
    )
    defaults.update(overrides)
    return CredencialDPP(**defaults)


class TestRelatorioReciclagemHTML:
    def test_html_contains_header_title(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred())
        assert "Fim de Vida" in output

    def test_html_contains_subtitle(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred())
        assert "Jequitinhonha" in output

    def test_html_shows_emitente(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred(emitente="RecicLar Sorocaba S.A."))
        assert "RecicLar Sorocaba S.A." in output

    def test_html_shows_product_name(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred(nome="Reciclagem Pack 75kWh"))
        assert "Reciclagem Pack 75kWh" in output

    def test_html_shows_materiais_recuperados(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred())
        assert "Materiais Recuperados" in output
        assert "litio_recuperado" in output
        assert "3.8 kg" in output
        assert "niquel_recuperado" in output

    def test_html_shows_rastreabilidade_reversa(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred())
        assert "Rastreabilidade Reversa" in output
        assert "Pack" in output
        assert "lula" in output  # Célula
        assert "Origem" in output

    def test_html_handles_none_credential(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(None)
        assert "credencial ausente" in output
        assert "<!DOCTYPE html>" in output
        assert "</html>" in output

    def test_html_verified_banner(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred())
        assert "Certificado de reciclagem verificado na Blockchain Cardano" in output
        assert "verified-badge" in output

    def test_html_is_self_contained(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred())
        assert "<!DOCTYPE html>" in output
        assert "<style>" in output
        assert "</html>" in output

    def test_html_lifecycle_flow(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred())
        assert "flow-step pack" in output
        assert "flow-step desmontagem" in output
        assert "flow-step reciclagem" in output

    def test_html_escapes_special_characters(self):
        rel = RelatorioReciclagemHTML()
        cred = _make_cred(emitente='Corp <script>alert("x")</script>')
        output = rel.gerar(cred)
        assert "<script>" not in output
        assert "&lt;script&gt;" in output

    def test_html_badge_metadata(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred(metodo_emissao="metadata"))
        assert 'emission-badge metadata' in output
        assert "Metadata" in output

    def test_html_badge_uverify(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred(metodo_emissao="uverify"))
        assert 'emission-badge uverify' in output
        assert "UVerify" in output

    def test_html_no_badge_when_none(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred())
        assert '<span class="emission-badge' not in output

    def test_html_teal_header(self):
        rel = RelatorioReciclagemHTML()
        output = rel.gerar(_make_cred())
        assert "#004d40" in output

    def test_html_with_real_payload(self):
        """Integration test using actual reciclagem payload."""
        from types import SimpleNamespace

        from verificador_dpp._payloads import payload_reciclagem
        from verificador_dpp.parser_credencial import ParserCredencial

        parser = ParserCredencial()
        env = {"ATOR1_TX": "tx1", "ATOR2_TX": "tx2", "ATOR3_TX": "tx3"}

        p_r, _, _ = payload_reciclagem(env)
        cred = parser.extrair_credencial(
            [SimpleNamespace(label="1990", json_metadata=p_r)]
        )

        rel = RelatorioReciclagemHTML()
        output = rel.gerar(cred)

        assert "RecicLar Sorocaba S.A." in output
        assert "Reciclagem Pack 75kWh" in output
        assert "Materiais Recuperados" in output
        assert "litio_recuperado" in output
        assert "Rastreabilidade Reversa" in output
        assert "Pack" in output
        assert "Origem" in output
        assert "Certificado de reciclagem verificado na Blockchain Cardano" in output
        assert "<!DOCTYPE html>" in output
