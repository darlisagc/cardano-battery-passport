"""Verificador DPP DIRETO via Blockfrost + PyCardano - opcao A.

Le os metadados da transacao via Blockfrost, faz parse do payload
UVerify e segue as referencias `cert_*_credential_tx` para
reconstruir a cadeia completa.

Uso:
    PYTHONPATH=src python -m verificador_dpp.verificador_direto
    PYTHONPATH=src python -m verificador_dpp.verificador_direto <txHashPack>

Fluxo da verificacao (a partir do TX_HASH_PACK):
    1. Buscar credencial do PACK    via Blockfrost
    2. Seguir cert_celula_credential_tx -> credencial da CELULA
    3. Seguir cert_origem_credential_tx -> credencial da ORIGEM
    4. Montar PassaporteBateria(origem, celula, pack) e imprimir
"""

from __future__ import annotations

import os
import sys
import traceback

from dotenv import load_dotenv

from .cliente_blockfrost import ClienteBlockfrost
from .modelos import PassaporteBateria
from .parser_credencial import ParserCredencial
from .relatorio_passaporte import RelatorioPassaporte


def main() -> None:
    # Carrega variaveis do .env (BLOCKFROST_PROJECT_ID, TX_HASH_PACK)
    load_dotenv()

    # tx_hash do pack: por argumento na CLI ou via .env (TX_HASH_PACK).
    args = sys.argv[1:]
    tx_hash_pack = args[0] if args else os.environ.get("TX_HASH_PACK", "")
    project_id = os.environ.get("BLOCKFROST_PROJECT_ID", "")

    # Validacoes basicas
    if not tx_hash_pack:
        print(
            "ERRO: informe TX_HASH_PACK no .env ou como 1o argumento.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not project_id or project_id.startswith("preprodXXXX"):
        print(
            "ERRO: BLOCKFROST_PROJECT_ID nao configurado no .env.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("=" * 64)
    print("Verificador DPP DIRETO - Blockfrost + PyCardano")
    print("De Jequitinhonha a Europa: o Passaporte da Bateria")
    print("=" * 64)
    print()

    # Tres ajudantes:
    #   - ClienteBlockfrost:   le metadata via API do Blockfrost
    #   - ParserCredencial:    extrai CredencialDPP de uma resposta de metadata
    #   - RelatorioPassaporte: gera relatorio pt-BR
    blockfrost = ClienteBlockfrost(project_id)
    parser = ParserCredencial()
    relatorio = RelatorioPassaporte()

    try:
        # ------------------------------------------------------------
        # Passo 1 — Credencial do PACK (entrada do verificador).
        # GET /txs/<tx_hash_pack>/metadata via Blockfrost.
        # O parser scaneia todos os labels em busca de
        # "uverify_template_id" e converte para CredencialDPP.
        # ------------------------------------------------------------
        print("[1/4] Buscando credencial do pack...")
        credencial_pack = parser.extrair_credencial(
            blockfrost.buscar_metadados(tx_hash_pack)
        )
        print(f"      OK - {credencial_pack.nome}")
        print()

        # ------------------------------------------------------------
        # Passo 2 — Seguir cert_celula_credential_tx do pack para
        # encontrar a credencial da CELULA. Se nao houver referencia,
        # avisa e continua (nao quebra a cadeia).
        # ------------------------------------------------------------
        print("[2/4] Seguindo referencias para as celulas...")
        tx_celula = credencial_pack.referencias.get("celula_credential_tx")
        credencial_celula = None
        if tx_celula:
            credencial_celula = parser.extrair_credencial(
                blockfrost.buscar_metadados(tx_celula)
            )
            print(f"      OK - {credencial_celula.nome}")
        else:
            print("      AVISO: pack nao referencia credencial de celula.")
        print()

        # ------------------------------------------------------------
        # Passo 3 — Seguir cert_origem_credential_tx da celula para
        # chegar a ORIGEM (litio do Jequitinhonha).
        # ------------------------------------------------------------
        print("[3/4] Seguindo referencias para a origem do litio...")
        credencial_origem = None
        if credencial_celula is not None:
            tx_origem = credencial_celula.referencias.get(
                "origem_credential_tx"
            )
            if tx_origem:
                credencial_origem = parser.extrair_credencial(
                    blockfrost.buscar_metadados(tx_origem)
                )
                print(f"      OK - {credencial_origem.nome}")
            else:
                print(
                    "      AVISO: celula nao referencia credencial de origem."
                )
        print()

        # ------------------------------------------------------------
        # Passo 4 — Montar e imprimir o relatorio do passaporte.
        # PassaporteBateria agrupa as 3 credenciais; o RelatorioPassaporte
        # formata em pt-BR para console.
        # ------------------------------------------------------------
        print("[4/4] Montando relatorio do passaporte...")
        print()
        passaporte = PassaporteBateria(
            credencial_origem, credencial_celula, credencial_pack
        )
        print(relatorio.gerar(passaporte))

    except Exception as e:  # noqa: BLE001
        print(f"FALHA: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
