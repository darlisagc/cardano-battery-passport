"""Emissor DPP DIRETO via PyCardano - opcao A do hands-on (Secao 2).

NAO usa o uverify-sdk. Constroi a transacao do zero com
TransactionBuilder, anexa o payload DPP como metadata nativa do
Cardano e submete via Blockfrost.

Uso:
    PYTHONPATH=src python -m verificador_dpp.emissor_direto --ator origem
    PYTHONPATH=src python -m verificador_dpp.emissor_direto --ator celula
    PYTHONPATH=src python -m verificador_dpp.emissor_direto --ator pack
    PYTHONPATH=src python -m verificador_dpp.emissor_direto --ator reciclagem

Pre-requisitos no .env (ver .env.example):
    BLOCKFROST_PROJECT_ID  projeto preprod no blockfrost.io
    WALLET_MNEMONIC        24 palavras (TESTNET ONLY)
    ATOR1_TX, ATOR2_TX...  preenchidos sequencialmente apos cada emissao
"""

from __future__ import annotations

import argparse
import os
import sys

from blockfrost import ApiUrls
from dotenv import load_dotenv
from pycardano import (
    AuxiliaryData,
    BlockFrostChainContext,
    Metadata,
    TransactionBuilder,
    TransactionOutput,
)

from ._payloads import ATORES, PROXIMO_ATOR_ENV
from .wallet import carregar_carteira

# Label de metadata Cardano. Inteiro arbitrario >= 1 reservado pelo
# workshop. O verificador escaneia TODOS os labels procurando
# "uverify_template_id", entao mudar este numero nao quebra nada.
METADATA_LABEL = 1990


def emitir_direto(
    ator: str, env: dict[str, str], mnemonic: str, project_id: str
) -> str:
    payload, _serial, _gtin = ATORES[ator](env)
    payment_skey, address = carregar_carteira(mnemonic)

    context = BlockFrostChainContext(
        project_id=project_id,
        base_url=ApiUrls.preprod.value,
    )

    builder = TransactionBuilder(context)
    builder.add_input_address(address)
    # Self-pay minimo: 2 ADA voltam para o proprio endereco.
    builder.add_output(TransactionOutput(address, 2_000_000))
    builder.auxiliary_data = AuxiliaryData(
        Metadata({METADATA_LABEL: payload})
    )

    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=address,
    )
    context.submit_tx(signed_tx)
    return str(signed_tx.id)


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description=(
            "Emissor DPP direto via PyCardano "
            "(sem uverify-sdk). Opcao A do hands-on."
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
    project_id = os.environ.get("BLOCKFROST_PROJECT_ID", "").strip()

    if not mnemonic:
        sys.exit(
            "ERRO: defina WALLET_MNEMONIC no .env (24 palavras, TESTNET ONLY)."
        )
    if not project_id or project_id.startswith("preprodXXXX"):
        sys.exit("ERRO: defina BLOCKFROST_PROJECT_ID (preprod) no .env.")

    print(f"Emitindo DPP do Ator '{args.ator}' DIRETO via PyCardano...")
    print()

    tx_hash = emitir_direto(args.ator, dict(os.environ), mnemonic, project_id)
    proxima_chave = PROXIMO_ATOR_ENV[args.ator]

    print("OK - tx submetida em Cardano preprod.")
    print(f"  tx_hash:        {tx_hash}")
    print(
        f"  CardanoScan:    https://preprod.cardanoscan.io/transaction/{tx_hash}"
    )
    print()
    print(f"Proximo passo: cole no .env como  {proxima_chave}={tx_hash}")


if __name__ == "__main__":
    main()
