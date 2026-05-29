"""Emissor DPP via uverify-sdk — Opcao B do hands-on (Secao 2).

Usa o cliente oficial UVerify para construir + submeter a transacao;
o codigo Python so prove a callback de assinatura, que delega
ao PyCardano.

Analogia: na Opcao A voce monta a carta inteira e leva ao cartorio.
Aqui, o UVerify (cartorio) monta a carta para voce — voce so precisa
assinar para confirmar que e o dono da carteira.

Uso:
    uv run python -m verificador_dpp.emissor_sdk --ator origem
    uv run python -m verificador_dpp.emissor_sdk --ator celula
    uv run python -m verificador_dpp.emissor_sdk --ator pack
    uv run python -m verificador_dpp.emissor_sdk --ator reciclagem

Pre-requisitos no .env (ver .env.example):
    WALLET_MNEMONIC        24 palavras (TESTNET ONLY)
    ATOR1_TX, ATOR2_TX...  preenchidos sequencialmente apos cada emissao

Fluxo da emissao (cada `--ator <X>`):
    1. Carregar payload DPP do ator
    2. Derivar carteira HD do mnemonico
    3. Calcular o data_hash = sha256(gtin + serial) (impressao digital)
    4. Embrulhar tudo num CertificateData
    5. Verificar/limpar estado obsoleto (stale state)
    6. Garantir colateral para scripts Plutus V3
    7. Montar tx com tratamento de status codes
    8. Retry com exponential backoff (5 tentativas)

NOTA SOBRE O DESIGN — Workshop vs. Producao:

    Em producao, cada empresa da cadeia de suprimentos (MineraLitio,
    CellTech, PackMontadora, RecicLar) teria a sua propria carteira
    Cardano e cada produto fisico teria um serial unico. Nesse cenario
    o uso do UVerify SDK e direto:

        cert = CertificateData(hash=..., algorithm="SHA-256", metadata=payload)
        request = BuildTransactionRequest(type="default", address=addr, certificates=[cert])
        response = client.core.build_transaction(request)
        witness = sign_tx(response.unsigned_transaction)
        tx_hash = client.core.submit_transaction(response.unsigned_transaction, witness)

    Sem necessidade de nenhum dos workarounds deste modulo, porque:

    1. Carteiras separadas → cada empresa tem o seu proprio State Datum,
       sem contencao de UTXOs entre emissoes.
    2. Payloads unicos → cada produto tem um serial e data_hash diferente,
       logo nunca ha colisao com credenciais anteriores.
    3. Emissoes espacadas → na vida real as emissoes acontecem em
       momentos diferentes (dias, semanas), dando tempo de sobra para
       confirmacao on-chain entre cada uma.

    Neste workshop usamos UMA unica carteira para os 4 atores e
    re-executamos o mesmo codigo varias vezes, o que cria problemas
    que nao existiriam em producao:

    - RUN_ID: sufixo aleatorio para gerar data_hashes unicos por
      execucao, evitando colisao com credenciais de runs anteriores.
    - state_id: forcamos o backend a reutilizar um State Datum
      especifico, em vez de depender da auto-selecao (que pode
      falhar quando o UTXO mudou apos uma emissao anterior).
    - _aguardar_confirmacao: esperamos a tx ser confirmada on-chain
      antes de prosseguir, porque o proximo ator emite segundos
      depois da mesma carteira.
    - opt_out seletivo: so invalidamos o estado quando o erro e
      genuinamente o Bug #54 ("/ by zero"), e nao em qualquer 500.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
import webbrowser
from typing import Callable

from dotenv import find_dotenv, load_dotenv, set_key
from pycardano import (
    ExtendedSigningKey,
    Transaction,
    TransactionWitnessSet,
    VerificationKeyWitness,
)
from uverify_sdk import DataSignature, UVerifyClient, UVerifyApiError
from uverify_sdk.models import CertificateData
from uverify_sdk.models.transaction import BuildTransactionRequest

from ._payloads import ATORES, PROXIMO_ATOR_ENV, data_hash
from .relatorio_emissao_html import RelatorioEmissaoHTML
from .wallet import carregar_carteira


# =========================================================================
# Constantes de retry
# =========================================================================

MAX_ATTEMPTS = 5
INITIAL_DELAY_S = 5


# =========================================================================
# Callbacks de assinatura
# =========================================================================


def fazer_callback_assinatura(
    payment_skey: ExtendedSigningKey,
) -> Callable[[str], str]:
    """Cria a callback que o UVerify SDK chama para assinar a tx.

    Contrato (verificado contra uverify-sdk 0.1.8):
        sign_tx(unsigned_cbor_hex: str) -> witness_set_cbor_hex: str

    Fluxo da assinatura (4 passos):
        1. Decodificar a tx CBOR-hex que o UVerify acabou de montar
        2. Calcular o hash do transaction_body (32 bytes)
        3. Assinar esse hash com a chave de pagamento (Ed25519, 64 bytes)
        4. Embrulhar (vkey + signature) num TransactionWitnessSet e
           devolver em CBOR-hex para o SDK submeter
    """

    def sign_tx(unsigned_cbor_hex: str) -> str:
        # 1. Decodifica a transacao CBOR-hex montada pelo UVerify.
        tx = Transaction.from_cbor(unsigned_cbor_hex)

        # 2. Calcula o hash de 32 bytes do transaction_body — e isso
        #    que o Cardano espera ver assinado (nao a tx inteira).
        body_hash = tx.transaction_body.hash()

        # 3. Assinatura Ed25519 (64 bytes) sobre o body_hash.
        signature = payment_skey.sign(body_hash)

        # 4. Cardano espera a vkey Ed25519 de 32 bytes (sem o chain
        #    code de 32 bytes do CIP-1852 estendido).
        vkey = payment_skey.to_verification_key().to_non_extended()
        witness = VerificationKeyWitness(vkey, signature)

        # 5. Empacota (vkey + signature) num TransactionWitnessSet
        #    e devolve como CBOR-hex para o SDK submeter a rede.
        return TransactionWitnessSet(vkey_witnesses=[witness]).to_cbor_hex()

    return sign_tx


def fazer_callback_mensagem(
    payment_skey: ExtendedSigningKey,
) -> Callable[[str], DataSignature]:
    """Cria a callback CIP-8 para operacoes de estado do UVerify.

    O UVerify usa um fluxo de dois passos para gerenciar estados:
        1. Servidor envia um challenge (mensagem)
        2. Cliente assina com Ed25519 e devolve (vkey, signature)

    Retorna:
        Callable que recebe uma mensagem string e devolve DataSignature.
    """

    def sign_message(message: str) -> DataSignature:
        # 1. O servidor UVerify envia uma mensagem (challenge) como string.
        #    Convertemos para bytes para assinar.
        msg_bytes = message.encode("utf-8")

        # 2. Assinatura Ed25519 direta sobre os bytes da mensagem
        #    (diferente do sign_tx, que assina o body_hash da transacao).
        signature = payment_skey.sign(msg_bytes)

        # 3. Mesma conversao de vkey: remover o chain code do CIP-1852.
        vkey = payment_skey.to_verification_key().to_non_extended()

        # 4. Formato CIP-8: (chave_publica_hex, assinatura_hex).
        #    O UVerify valida isso server-side para autenticar a carteira.
        return DataSignature(
            key=bytes(vkey).hex(),
            signature=signature.hex(),
        )

    return sign_message


# =========================================================================
# Helpers de infraestrutura
# =========================================================================


def _aguardar_confirmacao(client: UVerifyClient, tx_hash: str, timeout: int = 60) -> bool:
    """Poll GET /api/v1/transaction/confirm/{hash} ate confirmacao ou timeout.

    Analogia: como ficar "atualizando a pagina" ate o status do pedido
    mudar de "processando" para "concluido". A cada 5s perguntamos ao
    UVerify se a tx ja foi confirmada na blockchain.
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            # O endpoint retorna 200 quando a tx tem pelo menos
            # 1 confirmacao na blockchain (incluida em um bloco).
            resp = client._session.get(
                f"{client._base_url}/api/v1/transaction/confirm/{tx_hash}",
                timeout=15,
            )
            if resp.status_code == 200:
                return True
        except Exception:
            pass  # Falha de rede — tentaremos novamente no proximo ciclo.
        time.sleep(5)
    return False


def _preparar_colateral(
    client: UVerifyClient,
    address: str,
    sign_tx: Callable[[str], str],
) -> None:
    """Garante que a carteira tem um UTXO de colateral >= 5 ADA.

    UVerify usa smart contracts Plutus V3 que exigem colateral dedicado.
    Este endpoint cria um split tx que separa 5 ADA em um UTXO dedicado.
    """
    # Este endpoint nao faz parte do SDK oficial — chamamos a REST API
    # diretamente. Ele verifica se a carteira ja tem um UTXO >= 5 ADA
    # marcado como colateral. Se nao, retorna uma tx de "split" para criar.
    print("  [colateral] Verificando colateral...")
    try:
        resp = client._session.post(
            f"{client._base_url}/api/v1/transaction/prepare-collateral",
            json={"senderAddress": address},
            timeout=30,
        )
    except Exception as e:
        print(f"  [colateral] Falha na requisicao: {e}")
        return  # Nao-critico: a emissao tentara mesmo sem colateral preparado.

    if not resp.ok:
        print(f"  [colateral] API retornou {resp.status_code} — prosseguindo sem colateral dedicado.")
        return

    data = resp.json()
    # A API retorna um status message indicando se o colateral ja existe.
    status_msg = data.get("status", {}).get("message", "") or ""

    if "COLLATERAL_ALREADY_AVAILABLE" in status_msg.upper():
        print("  [colateral] ✓ Colateral ja disponivel.")
        return

    unsigned_tx = data.get("unsignedTransaction")
    if not unsigned_tx:
        print("  [colateral] ✓ Nenhuma acao necessaria.")
        return

    # Se chegou aqui, a API montou uma tx de split que separa 5 ADA
    # num UTXO dedicado. Precisamos assina-la e submeter.
    print("  [colateral] Criando UTXO de colateral (5 ADA)...")
    witness_set = sign_tx(unsigned_tx)
    tx_hash = client.core.submit_transaction(unsigned_tx, witness_set)
    print(f"  [colateral] Tx submetida: {tx_hash[:16]}...")

    # Aguardar confirmacao antes de prosseguir — o colateral precisa
    # estar on-chain antes da emissao do certificado.
    if _aguardar_confirmacao(client, tx_hash):
        print("  [colateral] ✓ Colateral confirmado.")
    else:
        print("  [colateral] AVISO: Timeout aguardando confirmacao — prosseguindo.")


def _verificar_e_limpar_estado(
    client: UVerifyClient,
    address: str,
    sign_message: Callable[[str], DataSignature],
) -> str | None:
    """Verifica estado existente e retorna o state_id para reuso.

    Retorna o state_id encontrado para que a emissao possa forcar
    o backend a reutilizar esse State Datum (evita criar um novo
    UTXO e pagar minAda adicional). Se nao houver estado, retorna
    None e o backend criara um automaticamente.

    Apenas chama opt_out quando o erro contem "by zero" (Bug #54:
    State Datum de era Bootstrap incompativel). Outros erros 500
    sao tratados como transientes — retorna None e deixa o backend
    decidir.
    """
    # O "estado" (State Datum) e uma estrutura on-chain que o smart
    # contract do UVerify usa para rastrear as emissoes da carteira.
    # Analogia: como um "cadastro" da carteira no cartorio.
    print("  [estado] Verificando estado existente...")
    try:
        # get_user_info() requer assinatura CIP-8 para autenticar
        # a carteira (prova que somos donos do endereco).
        resp = client.get_user_info(address, sign_message=sign_message)
        if resp.state:
            # Estado valido — sera reutilizado na emissao (custo menor).
            print(
                f"  [estado] ✓ Estado valido encontrado "
                f"(id={resp.state.id[:12]}..., countdown={resp.state.countdown})"
            )
            return resp.state.id
        else:
            # Sem estado — sera criado automaticamente na primeira emissao
            # (custa ~2 ADA extras, que podem ser recuperados via opt_out).
            print("  [estado] ✓ Nenhum estado — sera criado na emissao.")
            return None
    except UVerifyApiError as e:
        error_body = str(e.response_body).lower() if e.response_body else ""
        if "by zero" in error_body:
            # Bug #54 do UVerify: carteiras com State Datum de uma era
            # anterior do Bootstrap causam "/ by zero" no backend.
            # Solucao: invalidar o estado via opt_out e criar um novo.
            print("  [estado] Estado obsoleto detectado (/ by zero) — tentando opt_out...")
            try:
                # opt_out com state_id="" invalida todos os estados
                # da carteira, permitindo criar um novo na emissao.
                client.opt_out(address, state_id="", sign_message=sign_message)
                print("  [estado] ✓ Estado invalidado com sucesso.")
                # Aguardar o burn do state token on-chain antes de prosseguir.
                time.sleep(15)
            except Exception as opt_err:
                print(f"  [estado] AVISO: opt_out falhou ({opt_err}). Prosseguindo...")
            return None
        else:
            print(f"  [estado] AVISO: Erro ao consultar estado ({e.status_code}). Prosseguindo...")
            return None
    except Exception as e:
        print(f"  [estado] AVISO: Nao foi possivel verificar estado ({e}). Prosseguindo...")
        return None


def _emitir_com_tratamento(
    client: UVerifyClient,
    address: str,
    cert: CertificateData,
    sign_tx: Callable[[str], str],
    sign_message: Callable[[str], DataSignature],
    state_id: str | None = None,
) -> str:
    """Emite certificado com tratamento de status codes da API.

    Verifica a resposta do build para COLLATERAL_REQUIRED e
    PENDING_TRANSACTION, tratando cada caso antes de prosseguir.

    Args:
        state_id: Se fornecido, forca o backend a reutilizar esse
            State Datum em vez de selecionar automaticamente o mais
            barato. Isso evita conflitos de UTXO ao emitir
            credenciais sequencialmente da mesma carteira.

    Retorna:
        tx_hash da transacao submetida.
    """
    # Montar o pedido de build. type="default" e o modo padrao do
    # UVerify para emissoes de certificados (outros tipos incluem
    # "bootstrap" e "update", usados internamente pelo smart contract).
    # Quando state_id e fornecido, forcamos o backend a usar esse
    # State Datum especifico (evita auto-selecao que pode falhar
    # quando o UTXO mudou apos uma emissao anterior).
    build_kwargs: dict = dict(
        type="default",
        address=address,
        certificates=[cert],
    )
    if state_id is not None:
        build_kwargs["state_id"] = state_id
        print(f"  [build] Forcando state_id={state_id[:12]}...")

    request = BuildTransactionRequest(**build_kwargs)

    # O build_transaction() pede ao UVerify para montar a tx CBOR
    # (com o smart contract Plutus V3 embutido). A resposta inclui:
    #   - unsigned_transaction: CBOR-hex da tx nao-assinada
    #   - status: mensagem indicando o resultado do build
    response = client.core.build_transaction(request)
    status_msg = (response.status.message or "").upper() if response.status else ""

    # Tratar COLLATERAL_REQUIRED — significa que a carteira nao tem
    # colateral preparado para executar o script Plutus.
    if "COLLATERAL" in status_msg and "REQUIRED" in status_msg:
        print("  Status: COLLATERAL_REQUIRED — preparando colateral...")
        _preparar_colateral(client, address, sign_tx)
        time.sleep(10)  # Aguardar confirmacao do colateral on-chain.
        request = BuildTransactionRequest(**build_kwargs)
        response = client.core.build_transaction(request)
        status_msg = (response.status.message or "").upper() if response.status else ""

    # Tratar PENDING_TRANSACTION — significa que a carteira tem uma
    # transacao anterior nao-confirmada (UTXO contention). Precisamos
    # aguardar para que o UTXO fique disponivel novamente.
    if "PENDING" in status_msg:
        print("  Status: PENDING_TRANSACTION — aguardando tx anterior...")
        time.sleep(30)
        request = BuildTransactionRequest(**build_kwargs)
        response = client.core.build_transaction(request)

    # Assinar a tx montada pelo UVerify e submeter a rede.
    witness_set = sign_tx(response.unsigned_transaction)
    return client.core.submit_transaction(response.unsigned_transaction, witness_set)


# =========================================================================
# Funcao principal de emissao
# =========================================================================


def emitir_via_sdk(
    ator: str, env: dict[str, str], mnemonic: str
) -> tuple[str, str]:
    """Emite a credencial DPP via UVerify SDK; devolve (tx_hash, data_hash).

    Fluxo robusto com 5 camadas de protecao:
        1. Verificacao/limpeza de estado obsoleto
        2. Preparacao de colateral
        3. Tratamento de status codes (COLLATERAL_REQUIRED, PENDING)
        4. Exponential backoff (5 tentativas, delays 5→80s)
        5. Deteccao de carteira vazia (InsufficientFundsError)
    """

    # ----------------------------------------------------------------
    # Passo 1 — Construir o payload DPP e extrair gtin/serial.
    # ----------------------------------------------------------------
    payload, serial, gtin = ATORES[ator](env)

    # ----------------------------------------------------------------
    # Passo 2 — Carregar a carteira HD do mnemonico.
    # ----------------------------------------------------------------
    payment_skey, address = carregar_carteira(mnemonic)

    # ----------------------------------------------------------------
    # Passo 3 — Embrulhar tudo num CertificateData.
    # ----------------------------------------------------------------
    cert = CertificateData(
        hash=data_hash(gtin, serial),
        algorithm="SHA-256",
        metadata=payload,
    )

    # ----------------------------------------------------------------
    # Passo 4 — Criar o cliente UVerify e callbacks.
    # ----------------------------------------------------------------
    base_url = os.environ.get("UVERIFY_API_URL", "").strip()
    if base_url:
        client = UVerifyClient(base_url=base_url)
    else:
        print(
            "AVISO: UVERIFY_API_URL nao definida no .env — "
            "usando URL padrao do SDK (api.preprod.uverify.io)."
        )
        client = UVerifyClient()

    sign_tx_cb = fazer_callback_assinatura(payment_skey)
    sign_msg_cb = fazer_callback_mensagem(payment_skey)
    addr_str = str(address)

    # ----------------------------------------------------------------
    # Passo 5 — Verificar estado e obter state_id para reuso.
    # ----------------------------------------------------------------
    state_id = _verificar_e_limpar_estado(client, addr_str, sign_msg_cb)

    # ----------------------------------------------------------------
    # Passo 6 — Garantir colateral para scripts Plutus V3.
    # ----------------------------------------------------------------
    _preparar_colateral(client, addr_str, sign_tx_cb)

    # ----------------------------------------------------------------
    # Passo 7 — Emitir com retry e exponential backoff.
    #
    # Exponential backoff: a cada falha, o delay dobra (5, 10, 20, 40, 80s).
    # Isso evita sobrecarregar a API e da tempo para a rede propagar
    # transacoes anteriores. Analogia: se o cartorio esta ocupado,
    # voce espera um pouco mais a cada tentativa, em vez de ficar
    # batendo na porta sem parar.
    # ----------------------------------------------------------------
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            tx_hash = _emitir_com_tratamento(
                client, addr_str, cert, sign_tx_cb, sign_msg_cb,
                state_id=state_id,
            )
            # Aguardar confirmacao on-chain antes de retornar, para
            # que o State Datum UTXO esteja settled quando o proximo
            # ator tentar emitir da mesma carteira.
            print("  Aguardando confirmacao on-chain antes de prosseguir...")
            if _aguardar_confirmacao(client, tx_hash):
                print("  ✓ Transacao confirmada on-chain.")
            else:
                print("  AVISO: Timeout aguardando confirmacao — prosseguindo.")
            return tx_hash, cert.hash
        except UVerifyApiError as e:
            # Carteira vazia — fatal, nao adianta retry. O usuario
            # precisa pedir tADA no faucet antes de continuar.
            if "no utxos found" in str(e).lower():
                raise
            last_error = e
            # Calcula o delay: 5 * 2^(attempt-1) = 5, 10, 20, 40, 80s
            delay = INITIAL_DELAY_S * (2 ** (attempt - 1))
            if attempt < MAX_ATTEMPTS:
                print(
                    f"  Tentativa {attempt}/{MAX_ATTEMPTS} falhou "
                    f"(HTTP {e.status_code}), retentando em {delay}s..."
                )
                time.sleep(delay)
            else:
                print(f"  Todas as {MAX_ATTEMPTS} tentativas falharam.")

    raise last_error  # type: ignore[misc]


def main() -> None:
    # Carrega variaveis do .env (WALLET_MNEMONIC, ATOR*_TX)
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

    # Validacao basica: precisamos do mnemonico para assinar.
    mnemonic = os.environ.get("WALLET_MNEMONIC", "").strip()
    if not mnemonic:
        sys.exit(
            "ERRO: defina WALLET_MNEMONIC no .env (24 palavras, TESTNET ONLY)."
        )

    # ── RUN_ID: garante data_hashes unicos por execucao ──
    # Cada run completa (origem→celula→pack→reciclagem) usa o mesmo
    # RUN_ID. Na primeira emissao de um run, geramos um ID aleatorio
    # de 4 hex chars e salvamos no .env. Para iniciar um run novo,
    # apague RUN_ID do .env ou defina um novo valor.
    env_path = find_dotenv(usecwd=True) or ".env"
    run_id = os.environ.get("RUN_ID", "").strip()
    if not run_id:
        import secrets
        run_id = secrets.token_hex(2)  # 4 hex chars, e.g. "a3f1"
        set_key(env_path, "RUN_ID", run_id, quote_mode="never")
        os.environ["RUN_ID"] = run_id
        print(f"Novo RUN_ID gerado: {run_id}")
    else:
        print(f"Usando RUN_ID existente: {run_id}")

    print(f"Emitindo DPP do Ator '{args.ator}' via UVerify SDK (preprod)...")
    print()

    # Executa o fluxo robusto de emissao.
    tx_hash, dh = emitir_via_sdk(args.ator, dict(os.environ), mnemonic)
    proxima_chave = PROXIMO_ATOR_ENV[args.ator]

    # Imprime tx_hash + data_hash e atualiza .env automaticamente.
    print()
    print("OK - credencial publicada em Cardano preprod.")
    print(f"  tx_hash:        {tx_hash}")
    print(f"  data_hash:      {dh}")
    print(
        f"  Cexplorer:      https://preprod.cexplorer.io/tx/{tx_hash}"
    )
    print()

    # Auto-atualiza .env (sem aspas, no formato existente)
    atualizadas = [f"{proxima_chave}={tx_hash}"]
    set_key(env_path, proxima_chave, tx_hash, quote_mode="never")
    if args.ator == "pack":
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


if __name__ == "__main__":
    main()
