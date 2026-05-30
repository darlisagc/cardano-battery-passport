"""Tests for emissor_sdk.py — SDK base URL validation, CertificateData construction,
and reciclagem report wiring."""

import os
from unittest.mock import MagicMock, patch

import pytest

# Common patches for internal helpers that interact with the blockchain.
# These are no-ops so the tests can focus on URL selection and cert construction.
_PATCH_ESTADO = patch(
    "verificador_dpp.emissor_sdk._verificar_e_limpar_estado", return_value=None
)
_PATCH_COLATERAL = patch(
    "verificador_dpp.emissor_sdk._preparar_colateral"
)
_PATCH_CONFIRMAR = patch(
    "verificador_dpp.emissor_sdk._aguardar_confirmacao", return_value=True
)


def _make_mock_emitir(tx_hash: str = "fake_tx_hash"):
    """Create a patch for _emitir_com_tratamento that returns tx_hash."""
    return patch(
        "verificador_dpp.emissor_sdk._emitir_com_tratamento",
        return_value=tx_hash,
    )


# ── Base URL selection logic ─────────────────────────────────────────


class TestBaseUrlSelection:
    """Test that emitir_via_sdk reads UVERIFY_API_URL correctly."""

    @_PATCH_CONFIRMAR
    @_PATCH_COLATERAL
    @_PATCH_ESTADO
    @patch("verificador_dpp.emissor_sdk.carregar_carteira")
    @patch("verificador_dpp.emissor_sdk.UVerifyClient")
    def test_uses_env_base_url_when_set(
        self, mock_client_cls, mock_wallet, _estado, _col, _conf
    ):
        """When UVERIFY_API_URL is set, it should be passed as base_url."""
        from verificador_dpp.emissor_sdk import emitir_via_sdk

        mock_skey = MagicMock()
        mock_addr = MagicMock()
        mock_wallet.return_value = (mock_skey, mock_addr)
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        env = {"UVERIFY_API_URL": "https://custom.api.example.com"}

        with _make_mock_emitir(), patch.dict(os.environ, env, clear=False):
            emitir_via_sdk("origem", env, "fake mnemonic words " * 3)

        # UVerifyClient should have been called with base_url
        mock_client_cls.assert_called_once_with(
            base_url="https://custom.api.example.com"
        )

    @_PATCH_CONFIRMAR
    @_PATCH_COLATERAL
    @_PATCH_ESTADO
    @patch("verificador_dpp.emissor_sdk.carregar_carteira")
    @patch("verificador_dpp.emissor_sdk.UVerifyClient")
    def test_uses_default_when_env_not_set(
        self, mock_client_cls, mock_wallet, _estado, _col, _conf
    ):
        """When UVERIFY_API_URL is empty/missing, should use default (no base_url)."""
        from verificador_dpp.emissor_sdk import emitir_via_sdk

        mock_skey = MagicMock()
        mock_addr = MagicMock()
        mock_wallet.return_value = (mock_skey, mock_addr)
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        env = {}

        with _make_mock_emitir(), patch.dict(
            os.environ, {"UVERIFY_API_URL": ""}, clear=False
        ):
            emitir_via_sdk("origem", env, "fake mnemonic words " * 3)

        # UVerifyClient should have been called without base_url
        mock_client_cls.assert_called_once_with()

    @_PATCH_CONFIRMAR
    @_PATCH_COLATERAL
    @_PATCH_ESTADO
    @patch("verificador_dpp.emissor_sdk.carregar_carteira")
    @patch("verificador_dpp.emissor_sdk.UVerifyClient")
    def test_strips_whitespace_from_url(
        self, mock_client_cls, mock_wallet, _estado, _col, _conf
    ):
        """Whitespace around UVERIFY_API_URL should be stripped."""
        from verificador_dpp.emissor_sdk import emitir_via_sdk

        mock_skey = MagicMock()
        mock_addr = MagicMock()
        mock_wallet.return_value = (mock_skey, mock_addr)
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        env = {}

        with _make_mock_emitir(), patch.dict(
            os.environ,
            {"UVERIFY_API_URL": "  https://api.preprod.uverify.io  "},
            clear=False,
        ):
            emitir_via_sdk("origem", env, "fake mnemonic words " * 3)

        mock_client_cls.assert_called_once_with(
            base_url="https://api.preprod.uverify.io"
        )

    @_PATCH_CONFIRMAR
    @_PATCH_COLATERAL
    @_PATCH_ESTADO
    @patch("verificador_dpp.emissor_sdk.carregar_carteira")
    @patch("verificador_dpp.emissor_sdk.UVerifyClient")
    def test_whitespace_only_url_falls_back_to_default(
        self, mock_client_cls, mock_wallet, _estado, _col, _conf
    ):
        """A whitespace-only UVERIFY_API_URL should fall back to default."""
        from verificador_dpp.emissor_sdk import emitir_via_sdk

        mock_skey = MagicMock()
        mock_addr = MagicMock()
        mock_wallet.return_value = (mock_skey, mock_addr)
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        env = {}

        with _make_mock_emitir(), patch.dict(
            os.environ, {"UVERIFY_API_URL": "   "}, clear=False
        ):
            emitir_via_sdk("origem", env, "fake mnemonic words " * 3)

        mock_client_cls.assert_called_once_with()


# ── CertificateData construction ─────────────────────────────────────


class TestCertificateDataConstruction:
    """Verify the CertificateData is built correctly with correct hash and metadata."""

    @_PATCH_CONFIRMAR
    @_PATCH_COLATERAL
    @_PATCH_ESTADO
    @patch("verificador_dpp.emissor_sdk.carregar_carteira")
    @patch("verificador_dpp.emissor_sdk.UVerifyClient")
    def test_certificate_hash_matches_data_hash(
        self, mock_client_cls, mock_wallet, _estado, _col, _conf
    ):
        from verificador_dpp._payloads import data_hash
        from verificador_dpp.emissor_sdk import emitir_via_sdk

        mock_skey = MagicMock()
        mock_addr = MagicMock()
        mock_wallet.return_value = (mock_skey, mock_addr)
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        with _make_mock_emitir() as mock_emitir, patch.dict(
            os.environ, {"UVERIFY_API_URL": ""}, clear=False
        ):
            tx, dh = emitir_via_sdk("origem", {}, "fake mnemonic words " * 3)

        # Verify data_hash returned matches expected.
        # env={} has no WALLET_MNEMONIC, so student suffix is "000000".
        expected_dh = data_hash("7891234560099", "ML-JQT-2026-05-000000")
        assert dh == expected_dh

        # Verify the cert passed to _emitir_com_tratamento has the same hash
        call_args = mock_emitir.call_args
        cert = call_args[0][2]  # 3rd positional arg is the CertificateData
        assert cert.hash == expected_dh

    @_PATCH_CONFIRMAR
    @_PATCH_COLATERAL
    @_PATCH_ESTADO
    @patch("verificador_dpp.emissor_sdk.carregar_carteira")
    @patch("verificador_dpp.emissor_sdk.UVerifyClient")
    def test_certificate_metadata_has_update_policy(
        self, mock_client_cls, mock_wallet, _estado, _col, _conf
    ):
        """The CertificateData.metadata should include uverify_update_policy."""
        from verificador_dpp.emissor_sdk import emitir_via_sdk

        mock_skey = MagicMock()
        mock_addr = MagicMock()
        mock_wallet.return_value = (mock_skey, mock_addr)
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        with _make_mock_emitir() as mock_emitir, patch.dict(
            os.environ, {"UVERIFY_API_URL": ""}, clear=False
        ):
            emitir_via_sdk("origem", {}, "fake mnemonic words " * 3)

        # Get the CertificateData that was passed to _emitir_com_tratamento
        call_args = mock_emitir.call_args
        cert = call_args[0][2]  # 3rd positional arg is the CertificateData
        assert cert.metadata["uverify_update_policy"] == "restricted"
        assert cert.metadata["uverify_template_id"] == "digitalProductPassport"

    @_PATCH_CONFIRMAR
    @_PATCH_COLATERAL
    @patch(
        "verificador_dpp.emissor_sdk._verificar_e_limpar_estado",
        return_value="test-state-id-123",
    )
    @patch("verificador_dpp.emissor_sdk.carregar_carteira")
    @patch("verificador_dpp.emissor_sdk.UVerifyClient")
    def test_state_id_forwarded_to_emitir(
        self, mock_client_cls, mock_wallet, _estado, _col, _conf
    ):
        """When _verificar_e_limpar_estado finds a state, state_id is forwarded."""
        from verificador_dpp.emissor_sdk import emitir_via_sdk

        mock_skey = MagicMock()
        mock_addr = MagicMock()
        mock_wallet.return_value = (mock_skey, mock_addr)
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        with _make_mock_emitir() as mock_emitir, patch.dict(
            os.environ, {"UVERIFY_API_URL": ""}, clear=False
        ):
            emitir_via_sdk("origem", {}, "fake mnemonic words " * 3)

        # Verify state_id="test-state-id-123" was passed to _emitir_com_tratamento
        call_kwargs = mock_emitir.call_args[1]
        assert call_kwargs["state_id"] == "test-state-id-123"

    @_PATCH_CONFIRMAR
    @_PATCH_COLATERAL
    @_PATCH_ESTADO
    @patch("verificador_dpp.emissor_sdk.carregar_carteira")
    @patch("verificador_dpp.emissor_sdk.UVerifyClient")
    def test_state_id_none_when_no_state(
        self, mock_client_cls, mock_wallet, _estado, _col, _conf
    ):
        """When _verificar_e_limpar_estado returns None, state_id=None is forwarded."""
        from verificador_dpp.emissor_sdk import emitir_via_sdk

        mock_skey = MagicMock()
        mock_addr = MagicMock()
        mock_wallet.return_value = (mock_skey, mock_addr)
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        with _make_mock_emitir() as mock_emitir, patch.dict(
            os.environ, {"UVERIFY_API_URL": ""}, clear=False
        ):
            emitir_via_sdk("origem", {}, "fake mnemonic words " * 3)

        # _PATCH_ESTADO returns None, so state_id=None should be passed
        call_kwargs = mock_emitir.call_args[1]
        assert call_kwargs["state_id"] is None


# ── Reciclagem report wiring ─────────────────────────────────────────


class TestReciclagemReportWiring:
    """Verify that reciclagem report imports exist and wiring logic works."""

    def test_emissor_sdk_imports_relatorio_reciclagem(self):
        """emissor_sdk should export RelatorioReciclagemHTML."""
        from verificador_dpp.emissor_sdk import RelatorioReciclagemHTML

        assert RelatorioReciclagemHTML is not None

    def test_emissor_sdk_imports_classificar_campos(self):
        """emissor_sdk should export classificar_campos."""
        from verificador_dpp.emissor_sdk import classificar_campos

        assert callable(classificar_campos)

    def test_emissor_sdk_imports_credencial_dpp(self):
        """emissor_sdk should export CredencialDPP."""
        from verificador_dpp.emissor_sdk import CredencialDPP

        assert CredencialDPP is not None

    def test_emissor_direto_imports_relatorio_reciclagem(self):
        """emissor_direto should export RelatorioReciclagemHTML."""
        from verificador_dpp.emissor_direto import RelatorioReciclagemHTML

        assert RelatorioReciclagemHTML is not None

    def test_emissor_direto_imports_classificar_campos(self):
        """emissor_direto should export classificar_campos."""
        from verificador_dpp.emissor_direto import classificar_campos

        assert callable(classificar_campos)

    def test_emissor_direto_imports_credencial_dpp(self):
        """emissor_direto should export CredencialDPP."""
        from verificador_dpp.emissor_direto import CredencialDPP

        assert CredencialDPP is not None

    def test_reciclagem_report_from_payload(self):
        """RelatorioReciclagemHTML generates valid HTML from a reciclagem payload."""
        from verificador_dpp._payloads import ATORES
        from verificador_dpp.modelos import CredencialDPP
        from verificador_dpp.parser_credencial import classificar_campos
        from verificador_dpp.relatorio_reciclagem_html import RelatorioReciclagemHTML

        env = {
            "ATOR1_TX": "tx_origem_abc123",
            "ATOR2_TX": "tx_celula_def456",
            "ATOR3_TX": "tx_pack_ghi789",
        }
        payload, _, _ = ATORES["reciclagem"](env)
        referencias, data_hashes, materiais = classificar_campos(payload)
        cred = CredencialDPP(
            nome=payload.get("name"),
            emitente=payload.get("issuer"),
            gtin=payload.get("gtin"),
            origem=payload.get("origin"),
            fabricado_em=payload.get("manufactured"),
            pegada_carbono=payload.get("carbon_footprint"),
            conteudo_reciclado=payload.get("recycled_content"),
            materiais=materiais,
            referencias=referencias,
            data_hashes=data_hashes,
            tx_hash="fake_tx_hash_reciclagem",
        )
        html = RelatorioReciclagemHTML().gerar(cred)

        # Verify it's valid HTML with the teal theme
        assert "<!DOCTYPE html>" in html
        assert "#004d40" in html
        # Verify it contains the emitter name
        assert "RecicLar" in html
        # Verify materials section is present
        assert "Materiais Recuperados" in html
        # Verify reverse traceability section is present
        assert "Rastreabilidade Reversa" in html
        # Verify reference tx hashes appear
        assert "tx_origem_abc123" in html
        assert "tx_celula_def456" in html
        assert "tx_pack_ghi789" in html
