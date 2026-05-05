"""Verificador DPP via uverify-sdk - opcao B do hands-on (Secao 3).

Usa a API publica do UVerify (sem Blockfrost). Uma chamada
HTTP traz a credencial completa - metadata, tx hash, timestamp.

Uso:
    PYTHONPATH=src python -m verificador_dpp.verificador_sdk
    PYTHONPATH=src python -m verificador_dpp.verificador_sdk \\
        --tx <txHashPack> --hash <dataHashPack>

Pre-requisitos no .env:
    TX_HASH_PACK     hash da tx do pack (Ator 3)
    DATA_HASH_PACK   sha256(gtin + serial) - impresso pelos emissores
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from dotenv import load_dotenv
from uverify_sdk import UVerifyApiError, UVerifyClient


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Verificador DPP via UVerify SDK. Opcao B do hands-on."
    )
    parser.add_argument(
        "--tx",
        default=os.environ.get("TX_HASH_PACK", "").strip(),
        help="tx hash a verificar (default: TX_HASH_PACK no .env)",
    )
    parser.add_argument(
        "--hash",
        dest="data_hash",
        default=os.environ.get("DATA_HASH_PACK", "").strip(),
        help="sha256(gtin + serial) (default: DATA_HASH_PACK no .env)",
    )
    args = parser.parse_args()

    if not args.tx:
        sys.exit("ERRO: informe --tx ou TX_HASH_PACK no .env.")
    if not args.data_hash:
        sys.exit(
            "ERRO: informe --hash ou DATA_HASH_PACK no .env.\n"
            "      O data_hash e impresso pelos emissores apos cada emissao."
        )

    print("=" * 64)
    print("Verificador DPP via UVerify SDK")
    print("=" * 64)
    print(f"  tx_hash:   {args.tx}")
    print(f"  data_hash: {args.data_hash}")
    print()

    client = UVerifyClient()  # default preprod
    try:
        cert = client.verify_by_transaction(args.tx, args.data_hash)
    except UVerifyApiError as e:
        sys.exit(f"FALHA: {e}")

    print("Credencial encontrada via UVerify:")
    print()
    # CertificateResponse e um dataclass; serializamos seu __dict__
    # para impressao legivel.
    print(json.dumps(_para_dict(cert), indent=2, ensure_ascii=False, default=str))


def _para_dict(obj):
    """Converte recursivamente dataclasses/Namespaces em dict para json.dumps."""
    if hasattr(obj, "__dict__") and not isinstance(obj, (str, bytes)):
        return {k: _para_dict(v) for k, v in vars(obj).items()}
    if isinstance(obj, list):
        return [_para_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _para_dict(v) for k, v in obj.items()}
    return obj


if __name__ == "__main__":
    main()
