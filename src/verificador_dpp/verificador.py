"""Verificador DPP — caminha cadeias heterogeneas (A + B/C).

Este modulo e o coracao do workshop. Ele recebe o tx_hash de um pack
de bateria (Ator 3) e "caminha para tras" pela cadeia de credenciais:

    pack → celula → origem do litio

Para cada credencial na cadeia, o verificador tenta duas estrategias
de leitura, escolhendo automaticamente conforme o metodo de emissao:

  1. **Metadata nativa Cardano** (via Blockfrost) — funciona para
     credenciais emitidas pelo `emissor_direto` (Opcao A), que grava
     os dados diretamente como metadata da transacao (label 1990).

  2. **API publica do UVerify** (via HTTP direto) — funciona para
     credenciais emitidas pelo `emissor_sdk` (Opcao B) ou pela
     interface web do UVerify (Opcao C). Neste caso, a metadata
     fica armazenada no backend do UVerify, indexada pelo par
     (tx_hash, data_hash).

O data_hash e o identificador unico do produto no UVerify, calculado
como sha256(gtin + serial). Para encontra-lo, o verificador usa:
  - Hints da cadeia (campo cert_*_data_hash da credencial anterior)
  - Extracao do redeemer on-chain (a fonte mais confiavel)
  - Extracao heuristica do inline datum (fallback)

Uso:
    uv run python -m verificador_dpp.verificador
    uv run python -m verificador_dpp.verificador <tx_hash_pack>

Pre-requisitos no .env:
    BLOCKFROST_PROJECT_ID  projeto preprod do Blockfrost
    TX_HASH_PACK           hash da tx do pack (Ator 3) — ponto de
                           entrada da cadeia de verificacao
    DATA_HASH_PACK         (opcional) hint do data_hash do pack;
                           usado se o pack foi emitido via B/C
"""

from __future__ import annotations

import json
import os
import re
import sys
import traceback
from typing import Any

import cbor2
import requests
from blockfrost import ApiUrls, BlockFrostApi
from dotenv import load_dotenv
from uverify_sdk import UVerifyApiError, UVerifyClient

from .modelos import CredencialDPP, PassaporteBateria
from .parser_credencial import ParserCredencial
from .relatorio_passaporte import RelatorioPassaporte


# =====================================================================
# SECAO 1 — Extracao de candidatos a data_hash da blockchain
#
# Quando uma credencial foi emitida via UVerify (opcoes B ou C), o
# verificador precisa descobrir o `data_hash` para consultar a API.
# As funcoes abaixo extraem candidatos de duas fontes on-chain:
#   - Redeemer: contem o hash real do certificado (mais confiavel)
#   - Inline datum: contem sequencias de 32 bytes (heuristico)
# =====================================================================


def _walk_for_32byte(node: Any, out: list[str]) -> None:
    """Percorre recursivamente uma estrutura CBOR decodificada e coleta
    todas as sequencias de exatamente 32 bytes (formato hexadecimal).

    Por que 32 bytes? Porque um hash SHA-256 tem sempre 32 bytes, e o
    data_hash do UVerify e calculado com SHA-256. Entao qualquer
    sequencia de 32 bytes encontrada no datum e um *candidato* a ser
    o data_hash que precisamos.

    A funcao percorre listas, dicts, e tags CBOR recursivamente,
    adicionando cada sequencia de 32 bytes encontrada na lista `out`.
    """
    # Se o no atual e uma sequencia de bytes...
    if isinstance(node, bytes):
        # ...e tem exatamente 32 bytes (tamanho de um SHA-256),
        # adiciona como candidato em formato hexadecimal.
        if len(node) == 32:
            out.append(node.hex())
        return

    # Se e uma tag CBOR (envelope usado pelo Cardano/Plutus para
    # codificar constructors), entra no conteudo da tag.
    if isinstance(node, cbor2.CBORTag):
        _walk_for_32byte(node.value, out)

    # Se e uma lista ou tupla, percorre cada item.
    elif isinstance(node, (list, tuple)):
        for item in node:
            _walk_for_32byte(item, out)

    # Se e um dicionario, percorre cada valor.
    elif isinstance(node, dict):
        for v in node.values():
            _walk_for_32byte(v, out)


def _extrair_hashes_do_redeemer(
    blockfrost: BlockFrostApi, tx_hash: str
) -> list[str]:
    """Extrai os data_hashes reais dos certificados gravados no redeemer
    da transacao.

    Contexto tecnico (Cardano / Plutus / UVerify):
    -----------------------------------------------
    No smart contract do UVerify, cada transacao que emite um
    certificado inclui um "redeemer" — dado que o script valida
    on-chain. O redeemer tem esta estrutura:

        UVerifyStateRedeemer {
            purpose: StatePurpose,                    # campo 0
            certificates: List<UVerifyCertificate> {  # campo 1
                hash: ByteArray,       # <-- data_hash (o que queremos!)
                algorithm: String,     # ex: "SHA-256"
                issuer: ByteArray,     # credencial de pagamento
                extra: List<String>,   # metadata em chunks
            }
        }

    Caminho de navegacao na estrutura JSON do Blockfrost:
        redeemer.fields[1].list[*].fields[0].bytes

    Nota: o Blockfrost retorna objetos Namespace (nao dicts), por isso
    usamos getattr() em vez de acesso com colchetes.

    Retorna:
        Lista de data_hashes (strings hex de 64 caracteres = 32 bytes).
        Lista vazia se a tx nao tiver redeemers ou se a extracao falhar.
    """
    candidatos: list[str] = []

    # Passo 1 — Buscar todos os redeemers da transacao.
    # Transacoes emitidas via emissor_direto (opcao A) NAO tem redeemers
    # (usam metadata nativa), entao essa chamada pode retornar vazio.
    try:
        redeemers = blockfrost.transaction_redeemers(tx_hash)
    except Exception:
        return candidatos

    # Passo 2 — Para cada redeemer, buscar o conteudo do datum.
    for rd in redeemers or []:
        rd_hash = getattr(rd, "redeemer_data_hash", None)
        if not rd_hash:
            continue

        # Passo 3 — O Blockfrost guarda o conteudo do datum
        # separadamente, referenciado pelo hash. Buscamos aqui.
        try:
            datum = blockfrost.script_datum(rd_hash)
        except Exception:
            continue

        # Passo 4 — Navegar pela estrutura do datum para extrair
        # o hash do certificado.
        # Nota: Blockfrost retorna Namespace, nao dict, por isso
        # usamos getattr() em vez de ["chave"].
        jv = getattr(datum, "json_value", None)
        if jv is None:
            continue

        # fields[0] = purpose (ignoramos)
        # fields[1] = lista de certificados (o que queremos)
        fields = getattr(jv, "fields", None) or []
        if len(fields) < 2:
            continue

        # Cada item da lista e um UVerifyCertificate.
        # O primeiro campo (fields[0].bytes) e o data_hash.
        cert_list = getattr(fields[1], "list", None) or []
        for cert in cert_list:
            cert_fields = getattr(cert, "fields", None) or []
            if cert_fields:
                hash_hex = getattr(cert_fields[0], "bytes", "") or ""
                # Um hash SHA-256 em hexadecimal tem 64 caracteres
                # (32 bytes × 2 hex chars por byte).
                if len(hash_hex) == 64:
                    candidatos.append(hash_hex)

    return candidatos


def _extrair_candidatos_data_hash(
    blockfrost: BlockFrostApi, tx_hash: str
) -> list[str]:
    """Reune candidatos a data_hash de duas fontes on-chain.

    Fonte 1 — Redeemer (mais confiavel):
        Extrai o data_hash real do certificado UVerify gravado no
        redeemer da transacao. Funciona para todas as opcoes (A/B/C).

    Fonte 2 — Inline datum (fallback heuristico):
        Varre o inline datum do output de script buscando qualquer
        sequencia de 32 bytes. E um fallback porque nem toda sequencia
        de 32 bytes e necessariamente o data_hash — pode ser o ID do
        state datum ou o certificate_data_hash (hash dos certificados),
        que sao coisas diferentes.

    Retorna:
        Lista de strings hexadecimais (candidatos a data_hash).
        Os do redeemer vem primeiro (mais confiaveis).
    """
    candidatos: list[str] = []

    # Fonte 1 — buscar nos redeemers (mais confiavel).
    candidatos.extend(_extrair_hashes_do_redeemer(blockfrost, tx_hash))

    # Fonte 2 — buscar no inline datum (fallback heuristico).
    # Lemos os outputs (UTXOs) da transacao e procuramos inline datums.
    try:
        utxos = blockfrost.transaction_utxos(tx_hash)
    except Exception:
        return candidatos

    for output in getattr(utxos, "outputs", []) or []:
        # Inline datum e o dado Plutus gravado diretamente no output
        # da transacao (em vez de referenciar por hash).
        inline_datum_hex = getattr(output, "inline_datum", None)
        if not inline_datum_hex:
            continue
        try:
            # Decodifica o CBOR (formato binario usado pelo Cardano)
            # para uma estrutura Python (listas, dicts, bytes, etc).
            obj = cbor2.loads(bytes.fromhex(inline_datum_hex))
        except Exception:
            continue
        # Percorre a estrutura buscando sequencias de 32 bytes.
        _walk_for_32byte(obj, candidatos)

    return candidatos


# =====================================================================
# SECAO 2 — Conversao de respostas UVerify para CredencialDPP
#
# O UVerify retorna a metadata do certificado de diferentes formas:
#   - Como string JSON (quando veio do SDK)
#   - Como dict Python (quando ja foi parseado)
#   - Como Namespace object (do blockfrost-python)
#
# As funcoes abaixo normalizam esses formatos e extraem os campos
# relevantes para construir um objeto CredencialDPP.
# =====================================================================


def _normalize_metadata(meta: Any) -> dict | None:
    """Normaliza a metadata para um dicionario Python.

    A metadata pode chegar em tres formatos diferentes:
      - String JSON: '{"name": "Litio", ...}' → faz json.loads()
      - Dict Python: {"name": "Litio", ...}   → retorna como esta
      - Namespace:   Namespace(name="Litio")   → converte para dict

    Retorna None se nao conseguir converter.
    """
    # Caso 1: metadata e uma string JSON — precisa decodificar.
    if isinstance(meta, str):
        try:
            return json.loads(meta)
        except Exception:
            return None
    # Caso 2: ja e um dict — retorna direto.
    if isinstance(meta, dict):
        return meta
    # Caso 3: e um Namespace ou outro objeto — converte via vars().
    if hasattr(meta, "__dict__"):
        return dict(vars(meta))
    return None


def _credencial_from_uverify_response(cert: Any) -> CredencialDPP:
    """Converte um CertificateResponse do SDK UVerify para CredencialDPP.

    Esta funcao e usada quando o verificador chama o SDK do UVerify
    (via uverify.verify_by_transaction). Extrai o campo `metadata`
    da resposta e classifica cada chave do payload:

      - cert_*_credential_tx → vai para `referencias` (links para
        outras credenciais na cadeia)
      - cert_*_data_hash     → vai para `data_hashes` (hints para
        lookup UVerify das credenciais referenciadas)
      - mat_*                → vai para `materiais` (composicao)
      - demais campos        → mapeados diretamente (name, gtin, etc)
    """
    raw_meta = getattr(cert, "metadata", None)
    if raw_meta is None:
        raise ValueError("UVerify response sem metadata")
    meta = _normalize_metadata(raw_meta) or {}

    # Classificar cada campo do payload pela sua convencao de nome.
    referencias: dict[str, str] = {}
    materiais: dict[str, str] = {}
    data_hashes: dict[str, str] = {}
    for k, v in meta.items():
        if k.startswith("cert_") and k.endswith("_credential_tx"):
            # Ex: "cert_origem_credential_tx" → chave "origem_credential_tx"
            referencias[k[len("cert_"):]] = str(v)
        elif k.startswith("cert_") and k.endswith("_data_hash"):
            # Ex: "cert_origem_data_hash" → chave "origem_data_hash"
            data_hashes[k[len("cert_"):]] = str(v)
        elif k.startswith("mat_"):
            # Ex: "mat_niquel" → chave "niquel"
            materiais[k[len("mat_"):]] = str(v)

    return CredencialDPP(
        nome=meta.get("name"),
        emitente=meta.get("issuer"),
        gtin=meta.get("gtin"),
        origem=meta.get("origin"),
        fabricado_em=meta.get("manufactured"),
        pegada_carbono=meta.get("carbon_footprint"),
        conteudo_reciclado=meta.get("recycled_content"),
        materiais=materiais,
        referencias=referencias,
        data_hashes=data_hashes,
    )


# =====================================================================
# SECAO 3 — Lookup direto na API UVerify (sem usar o SDK)
#
# O SDK oficial do UVerify (uverify-sdk) faz `response.json()` para
# decodificar a resposta da API. Porem, a API retorna um historico
# completo de atualizacoes do `stateDatum` que pode ser MUITO
# profundamente aninhado (centenas de niveis). Isso causa um
# RecursionError no decodificador JSON do Python.
#
# Para contornar isso, fazemos o HTTP request diretamente e extraimos
# apenas o campo `extra` (onde esta a metadata) usando regex, sem
# precisar parsear o JSON inteiro.
# =====================================================================

# URL base da API UVerify para a rede preprod (testnet).
_UVERIFY_BASE = "https://api.preprod.uverify.io"


def _verify_by_transaction_direct(
    tx_hash: str, data_hash: str,
) -> CredencialDPP:
    """Busca uma credencial na API UVerify e converte para CredencialDPP.

    Faz um GET direto na API publica do UVerify, sem usar o SDK,
    para evitar o RecursionError causado pela resposta JSON
    profundamente aninhada.

    A API retorna um JSON com muitos campos, mas so precisamos do
    campo `extra`, que contem a metadata do certificado (payload DPP)
    como uma string JSON escapada.

    Parametros:
        tx_hash:   hash da transacao Cardano (64 caracteres hex)
        data_hash: hash do produto = sha256(gtin + serial) (64 chars)

    Retorna:
        CredencialDPP com os dados do certificado.

    Levanta:
        UVerifyApiError: se a API retornar 404 (credencial nao encontrada)
        requests.HTTPError: para outros erros HTTP
        ValueError: se a resposta nao contiver o campo `extra`
    """
    # Passo 1 — Fazer o request HTTP para a API do UVerify.
    # O endpoint espera dois parametros: tx_hash e data_hash.
    url = (
        f"{_UVERIFY_BASE}/api/v1/verify/"
        f"by-transaction-hash/{tx_hash}/{data_hash}"
    )
    resp = requests.get(url, timeout=30)

    # Passo 2 — Verificar se a credencial foi encontrada.
    # 404 significa que o par (tx_hash, data_hash) nao existe no UVerify.
    if resp.status_code == 404:
        raise UVerifyApiError(f"UVerify API error 404: {resp.text}", 404)
    resp.raise_for_status()

    # Passo 3 — Extrair o campo "extra" do JSON bruto usando regex.
    # NAO fazemos json.loads() no response inteiro porque o campo
    # "stateDatum" e profundamente aninhado e causa RecursionError.
    #
    # O regex captura o conteudo entre aspas do campo "extra",
    # respeitando caracteres escapados (\" e \\).
    # Exemplo do que o regex encontra:
    #   "extra": "{\"name\": \"Litio\", ...}"
    m = re.search(r'"extra"\s*:\s*"((?:[^"\\]|\\.)*)"', resp.text)
    if not m:
        raise ValueError(
            f"UVerify response para tx {tx_hash} nao contem campo 'extra'."
        )

    # Passo 4 — Decodificar a string JSON extraida.
    # Como o valor de "extra" e uma string JSON dentro de outra string
    # JSON, as aspas e barras estao duplamente escapadas.
    # Precisamos reverter o escape: \" → " e \\ → \
    extra_json = m.group(1).replace('\\"', '"').replace("\\\\", "\\")
    meta = json.loads(extra_json)

    # Passo 5 — Classificar os campos da metadata (mesma logica de
    # _credencial_from_uverify_response, mas aqui com meta ja parseada).
    referencias: dict[str, str] = {}
    materiais: dict[str, str] = {}
    data_hashes: dict[str, str] = {}
    for k, v in meta.items():
        if k.startswith("cert_") and k.endswith("_credential_tx"):
            referencias[k[len("cert_"):]] = str(v)
        elif k.startswith("cert_") and k.endswith("_data_hash"):
            data_hashes[k[len("cert_"):]] = str(v)
        elif k.startswith("mat_"):
            materiais[k[len("mat_"):]] = str(v)

    return CredencialDPP(
        nome=meta.get("name"),
        emitente=meta.get("issuer"),
        gtin=meta.get("gtin"),
        origem=meta.get("origin"),
        fabricado_em=meta.get("manufactured"),
        pegada_carbono=meta.get("carbon_footprint"),
        conteudo_reciclado=meta.get("recycled_content"),
        materiais=materiais,
        referencias=referencias,
        data_hashes=data_hashes,
    )


# =====================================================================
# SECAO 4 — Funcao principal de busca de credencial
#
# Esta funcao tenta dois caminhos para encontrar uma credencial:
#   Caminho 1: metadata nativa Cardano (para emissor_direto / opcao A)
#   Caminho 2: API UVerify (para emissor_sdk / opcao B e UI / opcao C)
#
# E o ponto central de decisao do verificador — escolhe automaticamente
# o caminho correto conforme o que encontra na blockchain.
# =====================================================================


def buscar_credencial(
    blockfrost: BlockFrostApi,
    uverify: UVerifyClient,
    parser: ParserCredencial,
    tx_hash: str,
    data_hash_hint: str | None = None,
) -> CredencialDPP:
    """Busca uma credencial DPP na blockchain Cardano.

    Estrategia de busca (dois caminhos, em ordem):

    Caminho 1 — Metadata nativa Cardano:
        Usa o Blockfrost para ler a metadata da transacao (label 1990).
        Funciona para credenciais emitidas pelo `emissor_direto` (opcao A),
        que grava os dados como metadata nativa da transacao.

    Caminho 2 — API publica UVerify:
        Se a metadata nativa nao contiver uma credencial UVerify
        (campo `uverify_template_id`), consulta a API do UVerify usando
        candidatos a `data_hash`. Os candidatos vem de tres fontes:
          1. Hint fornecido pelo chamador (ex: DATA_HASH_PACK do .env
             ou cert_*_data_hash da credencial anterior na cadeia)
          2. Redeemer on-chain (hash real do certificado UVerify)
          3. Inline datum (sequencias de 32 bytes — heuristico)

    Parametros:
        blockfrost:      cliente Blockfrost configurado para preprod
        uverify:         cliente UVerify SDK (mantido por compatibilidade)
        parser:          parser de metadata nativa Cardano
        tx_hash:         hash da transacao a verificar (64 chars hex)
        data_hash_hint:  (opcional) data_hash ja conhecido, testado
                         primeiro para evitar buscas desnecessarias

    Retorna:
        CredencialDPP com os dados extraidos da credencial.

    Levanta:
        RuntimeError: se nenhum caminho conseguir encontrar a credencial.
    """

    # ----------------------------------------------------------------
    # Caminho 1 — Metadata nativa Cardano (para opcao A)
    #
    # O Blockfrost retorna a metadata da transacao como uma lista de
    # entradas (uma por label). O parser procura uma entrada com o
    # campo `uverify_template_id` e converte para CredencialDPP.
    # ----------------------------------------------------------------
    try:
        metadata_entries = blockfrost.transaction_metadata(tx_hash)
    except Exception:
        metadata_entries = None

    if metadata_entries:
        try:
            return parser.extrair_credencial(metadata_entries)
        except Exception:
            # A tx tem metadata, mas nao no formato UVerify nativo
            # (sem campo `uverify_template_id`). Provavelmente foi
            # emitida via SDK ou UI — vamos tentar o Caminho 2.
            pass

    # ----------------------------------------------------------------
    # Caminho 2 — API publica UVerify (para opcoes B e C)
    #
    # Precisamos do data_hash para consultar a API. Reunimos candidatos
    # de tres fontes, na ordem de confiabilidade:
    #   1. Hint do chamador (se fornecido)
    #   2. Redeemer on-chain (mais confiavel)
    #   3. Inline datum (heuristico)
    # ----------------------------------------------------------------
    candidatos: list[str] = []

    # Fonte 1: hint fornecido pelo chamador (ex: cert_celula_data_hash
    # extraido da credencial do pack).
    if data_hash_hint:
        candidatos.append(data_hash_hint)

    # Fontes 2 e 3: redeemer e inline datum (via Blockfrost).
    candidatos.extend(_extrair_candidatos_data_hash(blockfrost, tx_hash))

    if not candidatos:
        raise RuntimeError(
            f"Tx {tx_hash}: sem metadata uverify_template_id e sem "
            "32-byte candidates no inline datum — nao consegui localizar."
        )

    # Tentar cada candidato ate encontrar um que a API do UVerify
    # reconheca. Usamos um set para evitar tentar o mesmo hash duas
    # vezes (pode acontecer se o hint tambem aparece no redeemer).
    last_error: Exception | None = None
    seen: set[str] = set()
    for dh in candidatos:
        if dh in seen:
            continue
        seen.add(dh)
        try:
            return _verify_by_transaction_direct(tx_hash, dh)
        except (UVerifyApiError, requests.HTTPError) as e:
            last_error = e
            continue

    raise RuntimeError(
        f"Tx {tx_hash}: nenhum dos {len(seen)} hashes-candidatos foi "
        f"reconhecido pelo UVerify (ultimo erro: {last_error})"
    )


# =====================================================================
# SECAO 5 — Ponto de entrada (CLI)
#
# Fluxo do verificador em 4 passos:
#   1. Buscar a credencial do PACK (Ator 3) — ponto de entrada.
#   2. Seguir a referencia para a CELULA (Ator 2).
#   3. Seguir a referencia para a ORIGEM do litio (Ator 1).
#   4. Montar o relatorio consolidado (passaporte da bateria).
#
# A cadeia e percorrida de tras para frente: comeca pelo pack
# (produto final) e vai ate a origem da materia-prima (litio).
# Isso simula o cenario real: um regulador europeu escaneia o QR
# do pack e quer rastrear toda a cadeia de suprimentos.
# =====================================================================


def main() -> None:
    """Ponto de entrada do verificador — executa os 4 passos de
    verificacao e imprime o passaporte consolidado."""

    # Carrega variaveis de ambiente do arquivo .env
    # (TX_HASH_PACK, DATA_HASH_PACK, BLOCKFROST_PROJECT_ID, etc).
    load_dotenv()

    # Ler os parametros necessarios do .env ou da linha de comando.
    args = sys.argv[1:]
    tx_hash_pack = (
        args[0] if args else os.environ.get("TX_HASH_PACK", "").strip()
    )
    data_hash_pack = os.environ.get("DATA_HASH_PACK", "").strip()
    project_id = os.environ.get("BLOCKFROST_PROJECT_ID", "").strip()

    # Validacoes basicas antes de comecar.
    if not tx_hash_pack:
        sys.exit("ERRO: informe TX_HASH_PACK no .env ou como 1o argumento.")
    if not project_id or project_id.startswith("preprodXXXX"):
        sys.exit("ERRO: BLOCKFROST_PROJECT_ID nao configurado no .env.")

    # Banner do workshop.
    print("=" * 64)
    print("Verificador DPP - Workshop Cardano")
    print("De Jequitinhonha a Europa: o Passaporte da Bateria")
    print("=" * 64)
    print()

    # Inicializar os clientes externos:
    #   - Blockfrost: acesso a blockchain Cardano preprod
    #   - UVerify:    API publica de verificacao de certificados
    #   - Parser:     interpreta metadata nativa Cardano
    #   - Relatorio:  formata o passaporte em portugues
    blockfrost = BlockFrostApi(
        project_id=project_id, base_url=ApiUrls.preprod.value
    )
    uverify = UVerifyClient()
    parser = ParserCredencial()
    relatorio = RelatorioPassaporte()

    try:
        # ============================================================
        # PASSO 1/4 — Buscar a credencial do PACK (Ator 3).
        #
        # O pack e o ponto de entrada da verificacao. O .env fornece
        # o tx_hash (TX_HASH_PACK) e opcionalmente o data_hash
        # (DATA_HASH_PACK) como hint para o lookup UVerify.
        # Se o pack foi emitido via emissor_direto (opcao A), o hint
        # e ignorado e a metadata nativa resolve diretamente.
        # ============================================================
        print("[1/4] Buscando credencial do pack...")
        cred_pack = buscar_credencial(
            blockfrost, uverify, parser, tx_hash_pack,
            data_hash_pack or None,
        )
        print(f"      OK - {cred_pack.nome}")
        print()

        # ============================================================
        # PASSO 2/4 — Seguir a referencia para a CELULA (Ator 2).
        #
        # A credencial do pack contem um campo
        # `cert_celula_credential_tx` que aponta para a tx da celula.
        # Tambem contem `cert_celula_data_hash` como hint para o
        # lookup UVerify (necessario se a celula foi emitida via B/C).
        # ============================================================
        print("[2/4] Seguindo referencias para as celulas...")
        tx_celula = cred_pack.referencias.get("celula_credential_tx")
        dh_celula = cred_pack.data_hashes.get("celula_data_hash")
        cred_celula = None
        if tx_celula:
            cred_celula = buscar_credencial(
                blockfrost, uverify, parser, tx_celula,
                dh_celula,
            )
            print(f"      OK - {cred_celula.nome}")
        else:
            print("      AVISO: pack nao referencia credencial de celula.")
        print()

        # ============================================================
        # PASSO 3/4 — Seguir a referencia para a ORIGEM (Ator 1).
        #
        # A credencial da celula contem `cert_origem_credential_tx`
        # e `cert_origem_data_hash` que apontam para a tx da origem
        # do litio (materia-prima).
        # ============================================================
        print("[3/4] Seguindo referencias para a origem do litio...")
        cred_origem = None
        if cred_celula is not None:
            tx_origem = cred_celula.referencias.get("origem_credential_tx")
            dh_origem = cred_celula.data_hashes.get("origem_data_hash")
            if tx_origem:
                cred_origem = buscar_credencial(
                    blockfrost, uverify, parser, tx_origem,
                    dh_origem,
                )
                print(f"      OK - {cred_origem.nome}")
            else:
                print(
                    "      AVISO: celula nao referencia credencial de origem."
                )
        print()

        # ============================================================
        # PASSO 4/4 — Montar e imprimir o relatorio consolidado.
        #
        # Com as tres credenciais (origem, celula, pack), monta o
        # PassaporteBateria e gera o relatorio em portugues.
        # ============================================================
        print("[4/4] Montando relatorio do passaporte...")
        print()
        passaporte = PassaporteBateria(cred_origem, cred_celula, cred_pack)
        print(relatorio.gerar(passaporte))

    except Exception as e:  # noqa: BLE001
        print(f"FALHA: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
