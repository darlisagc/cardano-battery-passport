"""Emissor DPP via uverify-sdk - opcao B do hands-on (Secao 2).

Usa o cliente oficial UVerify para construir + submeter a transacao;
o codigo Python so prove a callback de assinatura, que delega
ao PyCardano.

Uso:
    PYTHONPATH=src python -m verificador_dpp.emissor_sdk --ator origem
    PYTHONPATH=src python -m verificador_dpp.emissor_sdk --ator celula
    PYTHONPATH=src python -m verificador_dpp.emissor_sdk --ator pack
    PYTHONPATH=src python -m verificador_dpp.emissor_sdk --ator reciclagem

Pre-requisitos no .env (ver .env.example):
    WALLET_MNEMONIC        24 palavras (TESTNET ONLY)
    ATOR1_TX, ATOR2_TX...  preenchidos sequencialmente apos cada emissao
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Callable

from dotenv import load_dotenv
from pycardano import (
    ExtendedSigningKey,
    Transaction,
    TransactionWitnessSet,
    VerificationKeyWitness,
)
from uverify_sdk import UVerifyClient
from uverify_sdk.models import CertificateData

from ._payloads import ATORES, PROXIMO_ATOR_ENV, data_hash
from .wallet import carregar_carteira


def fazer_callback_assinatura(
    payment_skey: ExtendedSigningKey,
) -> Callable[[str], str]:
    """Devolve a callback que o UVerify SDK chama para assinar a tx.

    Contrato (verificado contra uverify-sdk 0.1.5):
        sign_tx(unsigned_cbor_hex: str) -> witness_set_cbor_hex: str
    """

    def sign_tx(unsigned_cbor_hex: str) -> str:
        tx = Transaction.from_cbor(unsigned_cbor_hex)
        body_hash = tx.transaction_body.hash()
        signature = payment_skey.sign(body_hash)
        # Cardano espera vkey Ed25519 normal de 32 bytes (sem chain code).
        vkey = payment_skey.to_verification_key().to_non_extended()
        witness = VerificationKeyWitness(vkey, signature)
        return TransactionWitnessSet(vkey_witnesses=[witness]).to_cbor_hex()

    return sign_tx


def emitir_via_sdk(
    ator: str, env: dict[str, str], mnemonic: str
) -> tuple[str, str]:
    payload, serial, gtin = ATORES[ator](env)
    payment_skey, address = carregar_carteira(mnemonic)

    cert = CertificateData(
        hash=data_hash(gtin, serial),
        algorithm="SHA-256",
        metadata=payload,
    )

    # UVerifyClient default base_url ja aponta para preprod
    # (https://api.preprod.uverify.io na versao 0.1.5).
    client = UVerifyClient()
    tx_hash = client.issue_certificates(
        address=str(address),
        certificates=[cert],
        sign_tx=fazer_callback_assinatura(payment_skey),
    )
    return tx_hash, cert.hash


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description=(
            "Emissor DPP via UVerify SDK. Opcao B do hands-on."
        )
    )
    parser.add_argument(
        "--ator",
        required=True,
        choices=list(ATORES.keys()),
        help="Qual ator emitir: origem, celula, pack ou reciclagem.",
    )
    args = parser.parse_args()

    mnemonic = os.environ.get("WALLET_MNEMONIC", "").strip()
    if not mnemonic:
        sys.exit(
            "ERRO: defina WALLET_MNEMONIC no .env (24 palavras, TESTNET ONLY)."
        )

    print(f"Emitindo DPP do Ator '{args.ator}' via UVerify SDK (preprod)...")
    print()
    tx_hash, dh = emitir_via_sdk(args.ator, dict(os.environ), mnemonic)
    proxima_chave = PROXIMO_ATOR_ENV[args.ator]

    print("OK - credencial publicada em Cardano preprod.")
    print(f"  tx_hash:        {tx_hash}")
    print(f"  data_hash:      {dh}")
    print(
        f"  CardanoScan:    https://preprod.cardanoscan.io/transaction/{tx_hash}"
    )
    print()
    print(f"Proximo passo: cole no .env como  {proxima_chave}={tx_hash}")


if __name__ == "__main__":
    main()
