"""Emissor DPP DIRETO via PyCardano — Opcao A do hands-on (Secao 2).

NAO usa o uverify-sdk. Constroi a transacao do zero com
TransactionBuilder, anexa o payload DPP como metadata nativa do
Cardano e submete via Blockfrost.

Analogia: e como escrever o documento inteiro na "ata do cartorio"
(metadata nativa) — qualquer pessoa que acesse o cartorio (blockchain)
pode ler os dados sem depender de terceiros.

Uso:
    uv run python -m verificador_dpp.emissor_direto --ator origem
    uv run python -m verificador_dpp.emissor_direto --ator celula
    uv run python -m verificador_dpp.emissor_direto --ator pack
    uv run python -m verificador_dpp.emissor_direto --ator reciclagem

Pre-requisitos no .env (ver .env.example):
    BLOCKFROST_PROJECT_ID  projeto preprod no blockfrost.io
    WALLET_MNEMONIC        24 palavras (TESTNET ONLY)
    ATOR1_TX, ATOR2_TX...  preenchidos sequencialmente apos cada emissao

Fluxo da emissao (cada `--ator <X>`):
    1. Carregar payload DPP do ator       (_payloads.py)
    2. Calcular data_hash e inclui-lo no payload
    3. Derivar carteira HD do mnemonico   (wallet.py)
    4. Conectar ao Blockfrost preprod
    5. Construir tx self-pay com metadata  (como enviar uma carta para
       si mesmo com o certificado como "anexo")
    6. Assinar com a chave de pagamento
    7. Submeter a rede preprod
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import webbrowser

from blockfrost import ApiUrls
from dotenv import find_dotenv, load_dotenv, set_key
from pycardano import (
    AuxiliaryData,
    BlockFrostChainContext,
    Metadata,
    TransactionBuilder,
)

from ._payloads import ATORES, PROXIMO_ATOR_ENV, data_hash
from .modelos import CredencialDPP
from .parser_credencial import classificar_campos
from .relatorio_emissao_html import RelatorioEmissaoHTML
from .relatorio_reciclagem_html import RelatorioReciclagemHTML
from .wallet import carregar_carteira

# Label de metadata Cardano — inteiro arbitrario >= 1 que identifica
# o "tipo" de anexo na transacao. Analogia: como um numero de
# formulario no cartorio. O verificador escaneia TODOS os labels
# procurando "uverify_template_id", entao mudar este numero nao
# quebra nada.
METADATA_LABEL = 1990


def emitir_direto(
    ator: str, env: dict[str, str], mnemonic: str, project_id: str
) -> tuple[str, str]:
    """Emite a credencial DPP do ator informado.

    Devolve (tx_hash, data_hash). O data_hash = sha256(gtin + serial)
    e a "impressao digital" do produto; util para inspecionar a
    credencial pela URL publica do UVerify ou como hint inicial no
    `verificador` quando uma cadeia mistura A com B/C.
    """

    # ----------------------------------------------------------------
    # Passo 1 — Construir o payload DPP do ator escolhido.
    # `_payloads.py` contem os dados de cada ator (origem, celula,
    # pack, reciclagem) seguindo o template digitalProductPassport.
    # Atores 2-4 exigem ATOR<N>_TX no env (para encadear).
    # ----------------------------------------------------------------
    payload, serial, gtin = ATORES[ator](env)
    dh = data_hash(gtin, serial)

    # Inclui o data_hash na metadata on-chain para que seja visivel
    # no Cexplorer e facilite lookups cruzados com a API do UVerify.
    payload["data_hash"] = dh

    # ----------------------------------------------------------------
    # Passo 2 — Carregar a carteira HD a partir do mnemonico.
    # Deriva chave de pagamento + endereco preprod via CIP-1852
    # (mesmo caminho que Eternl/Lace usam).
    # ----------------------------------------------------------------
    payment_skey, address = carregar_carteira(mnemonic)

    # ----------------------------------------------------------------
    # Passo 3 — Conectar ao Blockfrost preprod.
    # `BlockFrostChainContext` e a abstracao do PyCardano que
    # consulta UTxOs e submete transacoes via API do Blockfrost.
    # Analogia: e o nosso "portal de acesso" ao cartorio (blockchain).
    # ----------------------------------------------------------------
    context = BlockFrostChainContext(
        project_id=project_id,
        base_url=ApiUrls.preprod.value,
    )

    # ----------------------------------------------------------------
    # Passo 4 — Construir a transacao com TransactionBuilder.
    #   - input:           UTxOs encontrados no nosso endereco
    #   - output:          NENHUM explicito — `change_address` no
    #                      build_and_sign manda o leftover (input - fee)
    #                      de volta para o nosso proprio endereco
    #   - auxiliary_data:  payload DPP como metadata nativa Cardano
    #                      (como um "anexo" da transacao) sob o label 1990
    # Analogia: como enviar uma carta registrada para si mesmo —
    # o conteudo importante e o "anexo" (metadata), e voce so paga
    # a taxa de postagem (~0.18 tADA).
    # ----------------------------------------------------------------
    builder = TransactionBuilder(context)
    builder.add_input_address(address)
    builder.auxiliary_data = AuxiliaryData(
        Metadata({METADATA_LABEL: payload})
    )

    # ----------------------------------------------------------------
    # Passo 5 — Assinar a transacao com a chave de pagamento.
    # `build_and_sign` calcula o fee, escolhe os UTxOs (coin-selection),
    # monta o body, assina, e devolve uma Transaction completa.
    # ----------------------------------------------------------------
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=address,
    )

    # ----------------------------------------------------------------
    # Passo 6 — Submeter a transacao a rede preprod.
    # Em ~20-40s a tx aparece em Cexplorer preprod.
    # ----------------------------------------------------------------
    context.submit_tx(signed_tx)
    return str(signed_tx.id), dh


def main() -> None:
    # Carrega variaveis do .env (BLOCKFROST_PROJECT_ID, WALLET_MNEMONIC, ATOR*_TX)
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

    # Validacao basica: precisamos de mnemonico e project_id valido.
    mnemonic = os.environ.get("WALLET_MNEMONIC", "").strip()
    project_id = os.environ.get("BLOCKFROST_PROJECT_ID", "").strip()

    if not mnemonic:
        sys.exit(
            "ERRO: defina WALLET_MNEMONIC no .env (24 palavras, TESTNET ONLY)."
        )
    if not project_id or project_id.startswith("preprodXXXX"):
        sys.exit("ERRO: defina BLOCKFROST_PROJECT_ID (preprod) no .env.")

    # ── RUN_ID: garante data_hashes unicos por execucao ──
    env_path = find_dotenv(usecwd=True) or ".env"
    run_id = os.environ.get("RUN_ID", "").strip()
    if not run_id:
        import secrets
        run_id = secrets.token_hex(2)  # 4 hex chars
        set_key(env_path, "RUN_ID", run_id, quote_mode="never")
        os.environ["RUN_ID"] = run_id
        print(f"Novo RUN_ID gerado: {run_id}")
    else:
        print(f"Usando RUN_ID existente: {run_id}")

    print(f"Emitindo DPP do Ator '{args.ator}' DIRETO via PyCardano...")
    print()

    # Executa o fluxo de 6 passos definido em emitir_direto().
    tx_hash, dh = emitir_direto(args.ator, dict(os.environ), mnemonic, project_id)
    proxima_chave = PROXIMO_ATOR_ENV[args.ator]

    # Imprime resultado e atualiza .env automaticamente para encadear
    # o proximo ator. data_hash tambem vai pro .env (para a URL UVerify
    # ou como hint do verificador).
    print("OK - tx submetida em Cardano preprod.")
    print(f"  tx_hash:        {tx_hash}")
    print(f"  data_hash:      {dh}")
    print(
        f"  Cexplorer:      https://preprod.cexplorer.io/tx/{tx_hash}"
    )
    print()

    # Auto-atualiza .env (sem aspas, no formato existente)
    atualizadas = [f"{proxima_chave}={tx_hash}"]
    set_key(env_path, proxima_chave, tx_hash, quote_mode="never")
    if args.ator in ("pack", "reciclagem"):
        set_key(env_path, "TX_HASH_PACK", tx_hash, quote_mode="never")
        set_key(env_path, "DATA_HASH_PACK", dh, quote_mode="never")
        atualizadas.append(f"TX_HASH_PACK={tx_hash}")
        atualizadas.append(f"DATA_HASH_PACK={dh}")
    print("✓ .env atualizado:")
    for linha in atualizadas:
        print(f"    {linha}")

    # Gera relatorio HTML de emissao e abre no navegador.
    payload, _, _ = ATORES[args.ator](dict(os.environ))
    html = RelatorioEmissaoHTML().gerar(args.ator, payload, tx_hash, dh)
    with tempfile.NamedTemporaryFile(
        suffix=".html", delete=False, mode="w", encoding="utf-8"
    ) as f:
        f.write(html)
        html_path = f.name
    print(f"\nRelatorio de emissao salvo em: {html_path}")
    webbrowser.open(f"file://{html_path}")

    if args.ator == "reciclagem":
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
            tx_hash=tx_hash,
        )
        html_recicl = RelatorioReciclagemHTML().gerar(cred)
        with tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, mode="w", encoding="utf-8"
        ) as f:
            f.write(html_recicl)
            html_recicl_path = f.name
        print(f"Relatorio de reciclagem salvo em: {html_recicl_path}")
        webbrowser.open(f"file://{html_recicl_path}")


if __name__ == "__main__":
    main()
