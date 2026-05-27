"""Tests for modelos.py — CredencialDPP and PassaporteBateria dataclasses."""

import pytest

from verificador_dpp.modelos import CredencialDPP, PassaporteBateria


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


class TestCredencialDPP:
    def test_creation(self):
        c = _make_cred()
        assert c.nome == "Product"
        assert c.emitente == "Corp"

    def test_frozen(self):
        c = _make_cred()
        with pytest.raises(AttributeError):
            c.nome = "Changed"

    def test_optional_fields_can_be_none(self):
        c = _make_cred(
            nome=None,
            origem=None,
            fabricado_em=None,
            pegada_carbono=None,
            conteudo_reciclado=None,
        )
        assert c.nome is None
        assert c.origem is None

    def test_materiais_is_dict(self):
        c = _make_cred(materiais={"litio": "98%"})
        assert c.materiais == {"litio": "98%"}

    def test_referencias_is_dict(self):
        c = _make_cred(referencias={"origem_tx": "hash123"})
        assert c.referencias["origem_tx"] == "hash123"

    def test_data_hashes_is_dict(self):
        c = _make_cred(data_hashes={"origem_data_hash": "dh123"})
        assert c.data_hashes["origem_data_hash"] == "dh123"

    def test_metodo_emissao_default_none(self):
        c = _make_cred()
        assert c.metodo_emissao is None

    def test_metodo_emissao_metadata(self):
        c = _make_cred(metodo_emissao="metadata")
        assert c.metodo_emissao == "metadata"

    def test_metodo_emissao_uverify(self):
        c = _make_cred(metodo_emissao="uverify")
        assert c.metodo_emissao == "uverify"


class TestPassaporteBateria:
    def test_creation_with_all_fields(self):
        o = _make_cred(nome="Origem")
        c = _make_cred(nome="Celula")
        p = _make_cred(nome="Pack")
        pb = PassaporteBateria(origem=o, celula=c, pack=p)
        assert pb.origem.nome == "Origem"
        assert pb.celula.nome == "Celula"
        assert pb.pack.nome == "Pack"
        assert pb.reciclagem is None

    def test_creation_with_reciclagem(self):
        o = _make_cred(nome="Origem")
        c = _make_cred(nome="Celula")
        p = _make_cred(nome="Pack")
        r = _make_cred(nome="Reciclagem")
        pb = PassaporteBateria(origem=o, celula=c, pack=p, reciclagem=r)
        assert pb.reciclagem.nome == "Reciclagem"

    def test_creation_with_none_fields(self):
        pb = PassaporteBateria(origem=None, celula=None, pack=None)
        assert pb.origem is None
        assert pb.celula is None
        assert pb.pack is None
        assert pb.reciclagem is None

    def test_frozen(self):
        pb = PassaporteBateria(origem=None, celula=None, pack=None)
        with pytest.raises(AttributeError):
            pb.origem = _make_cred()

    def test_partial_chain(self):
        """A chain can have some credentials and some None."""
        o = _make_cred(nome="Origem")
        pb = PassaporteBateria(origem=o, celula=None, pack=None)
        assert pb.origem is not None
        assert pb.celula is None
