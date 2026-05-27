"""Tests for emissor_sdk.py — SDK base URL validation and CertificateData construction."""

import os
from unittest.mock import MagicMock, patch

import pytest


# ── Base URL selection logic ─────────────────────────────────────────


class TestBaseUrlSelection:
    """Test that emitir_via_sdk reads UVERIFY_API_URL correctly."""

    @patch("verificador_dpp.emissor_sdk.carregar_carteira")
    @patch("verificador_dpp.emissor_sdk.UVerifyClient")
    def test_uses_env_base_url_when_set(self, mock_client_cls, mock_wallet):
        """When UVERIFY_API_URL is set, it should be passed as base_url."""
        from verificador_dpp.emissor_sdk import emitir_via_sdk

        # Setup mocks
        mock_skey = MagicMock()
        mock_addr = MagicMock()
        mock_wallet.return_value = (mock_skey, mock_addr)
        mock_client = MagicMock()
        mock_client.issue_certificates.return_value = "fake_tx_hash"
        mock_client_cls.return_value = mock_client

        env = {"UVERIFY_API_URL": "https://custom.api.example.com"}

        with patch.dict(os.environ, env, clear=False):
            emitir_via_sdk("origem", env, "fake mnemonic words " * 3)

        # UVerifyClient should have been called with base_url
        mock_client_cls.assert_called_once_with(
            base_url="https://custom.api.example.com"
        )

    @patch("verificador_dpp.emissor_sdk.carregar_carteira")
    @patch("verificador_dpp.emissor_sdk.UVerifyClient")
    def test_uses_default_when_env_not_set(self, mock_client_cls, mock_wallet):
        """When UVERIFY_API_URL is empty/missing, should use default (no base_url)."""
        from verificador_dpp.emissor_sdk import emitir_via_sdk

        mock_skey = MagicMock()
        mock_addr = MagicMock()
        mock_wallet.return_value = (mock_skey, mock_addr)
        mock_client = MagicMock()
        mock_client.issue_certificates.return_value = "fake_tx_hash"
        mock_client_cls.return_value = mock_client

        env = {}

        with patch.dict(os.environ, {"UVERIFY_API_URL": ""}, clear=False):
            emitir_via_sdk("origem", env, "fake mnemonic words " * 3)

        # UVerifyClient should have been called without base_url
        mock_client_cls.assert_called_once_with()

    @patch("verificador_dpp.emissor_sdk.carregar_carteira")
    @patch("verificador_dpp.emissor_sdk.UVerifyClient")
    def test_strips_whitespace_from_url(self, mock_client_cls, mock_wallet):
        """Whitespace around UVERIFY_API_URL should be stripped."""
        from verificador_dpp.emissor_sdk import emitir_via_sdk

        mock_skey = MagicMock()
        mock_addr = MagicMock()
        mock_wallet.return_value = (mock_skey, mock_addr)
        mock_client = MagicMock()
        mock_client.issue_certificates.return_value = "fake_tx_hash"
        mock_client_cls.return_value = mock_client

        env = {}

        with patch.dict(
            os.environ,
            {"UVERIFY_API_URL": "  https://api.preprod.uverify.io  "},
            clear=False,
        ):
            emitir_via_sdk("origem", env, "fake mnemonic words " * 3)

        mock_client_cls.assert_called_once_with(
            base_url="https://api.preprod.uverify.io"
        )

    @patch("verificador_dpp.emissor_sdk.carregar_carteira")
    @patch("verificador_dpp.emissor_sdk.UVerifyClient")
    def test_whitespace_only_url_falls_back_to_default(
        self, mock_client_cls, mock_wallet
    ):
        """A whitespace-only UVERIFY_API_URL should fall back to default."""
        from verificador_dpp.emissor_sdk import emitir_via_sdk

        mock_skey = MagicMock()
        mock_addr = MagicMock()
        mock_wallet.return_value = (mock_skey, mock_addr)
        mock_client = MagicMock()
        mock_client.issue_certificates.return_value = "fake_tx_hash"
        mock_client_cls.return_value = mock_client

        env = {}

        with patch.dict(os.environ, {"UVERIFY_API_URL": "   "}, clear=False):
            emitir_via_sdk("origem", env, "fake mnemonic words " * 3)

        mock_client_cls.assert_called_once_with()


# ── CertificateData construction ─────────────────────────────────────


class TestCertificateDataConstruction:
    """Verify the CertificateData is built correctly with correct hash and metadata."""

    @patch("verificador_dpp.emissor_sdk.carregar_carteira")
    @patch("verificador_dpp.emissor_sdk.UVerifyClient")
    def test_certificate_hash_matches_data_hash(
        self, mock_client_cls, mock_wallet
    ):
        from verificador_dpp._payloads import data_hash
        from verificador_dpp.emissor_sdk import emitir_via_sdk

        mock_skey = MagicMock()
        mock_addr = MagicMock()
        mock_wallet.return_value = (mock_skey, mock_addr)
        mock_client = MagicMock()
        mock_client.issue_certificates.return_value = "fake_tx"
        mock_client_cls.return_value = mock_client

        with patch.dict(os.environ, {"UVERIFY_API_URL": ""}, clear=False):
            tx, dh = emitir_via_sdk("origem", {}, "fake mnemonic words " * 3)

        # Verify data_hash returned matches expected.
        # env={} has no WALLET_MNEMONIC, so student suffix is "000000".
        expected_dh = data_hash("7891234560099", "ML-JQT-2026-05-000000")
        assert dh == expected_dh

    @patch("verificador_dpp.emissor_sdk.carregar_carteira")
    @patch("verificador_dpp.emissor_sdk.UVerifyClient")
    def test_certificate_metadata_has_update_policy(
        self, mock_client_cls, mock_wallet
    ):
        """The CertificateData.metadata should include uverify_update_policy."""
        from verificador_dpp.emissor_sdk import emitir_via_sdk

        mock_skey = MagicMock()
        mock_addr = MagicMock()
        mock_wallet.return_value = (mock_skey, mock_addr)
        mock_client = MagicMock()
        mock_client.issue_certificates.return_value = "fake_tx"
        mock_client_cls.return_value = mock_client

        with patch.dict(os.environ, {"UVERIFY_API_URL": ""}, clear=False):
            emitir_via_sdk("origem", {}, "fake mnemonic words " * 3)

        # Get the CertificateData that was passed to issue_certificates
        call_args = mock_client.issue_certificates.call_args
        certs = call_args.kwargs.get("certificates") or call_args[1].get(
            "certificates"
        )
        assert len(certs) == 1
        cert = certs[0]
        assert cert.metadata["uverify_update_policy"] == "restricted"
        assert cert.metadata["uverify_template_id"] == "digitalProductPassport"
