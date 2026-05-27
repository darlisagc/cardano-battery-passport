"""Tests for relatorio_emissao_html.py — emission receipt HTML generation."""

from verificador_dpp.relatorio_emissao_html import RelatorioEmissaoHTML


def _sample_payload() -> dict:
    return {
        "uverify_template_id": "digitalProductPassport",
        "name": "Lote Litio Jequitinhonha 2026-03",
        "issuer": "MineraLitio Jequitinhonha Ltda.",
        "gtin": "7891234560013",
        "origin": "Aracuai, Vale do Jequitinhonha, MG, BR",
        "manufactured": "2026-03-13",
        "carbon_footprint": "4.2 kg CO2e / kg Li2CO3",
        "recycled_content": "0%",
        "mat_litio_carbonato": "98%",
        "mat_impurezas_ferro": "0.3%",
    }


TX_HASH = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
DATA_HASH = "f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0"


class TestRelatorioEmissaoHTML:
    def test_generates_valid_html(self):
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("origem", _sample_payload(), TX_HASH, DATA_HASH)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_contains_actor_title(self):
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("origem", _sample_payload(), TX_HASH, DATA_HASH)
        assert "Origem do Litio" in html

    def test_contains_actor_subtitle(self):
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("origem", _sample_payload(), TX_HASH, DATA_HASH)
        assert "MineraLitio Jequitinhonha" in html

    def test_contains_cexplorer_link(self):
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("origem", _sample_payload(), TX_HASH, DATA_HASH)
        assert f"https://preprod.cexplorer.io/tx/{TX_HASH}" in html

    def test_contains_tx_hash(self):
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("origem", _sample_payload(), TX_HASH, DATA_HASH)
        assert TX_HASH in html

    def test_contains_data_hash(self):
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("origem", _sample_payload(), TX_HASH, DATA_HASH)
        assert DATA_HASH in html

    def test_contains_payload_fields(self):
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("origem", _sample_payload(), TX_HASH, DATA_HASH)
        assert "MineraLitio Jequitinhonha Ltda." in html
        assert "7891234560013" in html
        assert "Aracuai" in html

    def test_contains_materiais(self):
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("origem", _sample_payload(), TX_HASH, DATA_HASH)
        assert "litio_carbonato" in html
        assert "98%" in html

    def test_contains_verified_banner(self):
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("origem", _sample_payload(), TX_HASH, DATA_HASH)
        assert "Emissao registrada na Blockchain Cardano" in html

    def test_reciclagem_actor_uses_teal(self):
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("reciclagem", _sample_payload(), TX_HASH, DATA_HASH)
        assert "#004d40" in html

    def test_celula_actor(self):
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("celula", _sample_payload(), TX_HASH, DATA_HASH)
        assert "Fabricacao das Celulas" in html

    def test_pack_actor(self):
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("pack", _sample_payload(), TX_HASH, DATA_HASH)
        assert "Montagem do Pack" in html

    def test_referencias_section(self):
        payload = _sample_payload()
        payload["cert_origem_credential_tx"] = "abc123def456abc123def456abc123def456abc123def456abc123def456abc123de"
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("celula", payload, TX_HASH, DATA_HASH)
        assert "Referencias na Cadeia" in html
        assert "preprod.cexplorer.io/tx/abc123" in html

    def test_escapes_html(self):
        payload = _sample_payload()
        payload["name"] = '<script>alert("xss")</script>'
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("origem", payload, TX_HASH, DATA_HASH)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_unknown_actor_falls_back(self):
        rel = RelatorioEmissaoHTML()
        html = rel.gerar("desconhecido", _sample_payload(), TX_HASH, DATA_HASH)
        assert "<!DOCTYPE html>" in html
