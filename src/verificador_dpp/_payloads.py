"""Payloads DPP (Digital Product Passport) de cada ator da cadeia de suprimentos.

Define os payloads — conjuntos de campos-chave/valor — que cada empresa
registra na blockchain Cardano como metadata de uma transacao.

Analogia: cada payload e como um "formulario padronizado" que a empresa
preenche e registra no cartorio (blockchain). O template
`digitalProductPassport` define quais campos existem (como um modelo
de formulario), e cada ator preenche com os dados do seu produto.

Cadeia de suprimentos (supply chain) — 4 atores:
    Ator 1: MineraLitio   — extracao do litio (materia-prima)
    Ator 2: CellTech      — fabricacao das celulas (referencia Ator 1)
    Ator 3: PackMontadora — montagem do pack de bateria (referencia Ator 2)
    Ator 4: RecicLar      — reciclagem (referencia Atores 1, 2 e 3)

Estrutura de cada payload:
  - Dados do produto: name, issuer, gtin, origin, manufactured, etc.
  - Composicao de materiais: campos mat_* (ex: mat_niquel = "80%")
  - Referencias (ponteiros) para credenciais anteriores na cadeia:
    campos ref_*_tx (tx_hash da tx anterior)
    Analogia: como links que permitem ao verificador "caminhar" pela
    cadeia de certificados, do produto final ate a materia-prima.
  - Data hashes (impressoes digitais SHA-256): campos ref_*_data_hash
    = sha256(gtin + serial) do produto referenciado. Necessarios para
    lookup na API do UVerify quando a credencial foi emitida via SDK/UI.
  - Privacy-split: uv_url_serial = sha256(serial). O serial nunca vai
    para a blockchain — so o hash. Analogia: como guardar a impressao
    digital em vez do documento original.

Todos os valores sao strings (exigencia do UVerify SDK / metadata nativa).

Usado pelos dois emissores:
  - emissor_direto.py (Opcao A — metadata nativa via PyCardano)
  - emissor_sdk.py    (Opcao B — via UVerify SDK)

Template: `digitalProductPassport`
Documentacao: https://docs.uverify.io/templates/built-in
"""

from __future__ import annotations

import sys
from hashlib import sha256
from typing import Callable


def _student_id(env: dict[str, str] | None) -> str:
    """Derive a deterministic suffix from WALLET_MNEMONIC + RUN_ID.

    Each student in the workshop has a unique mnemonic, so every wallet
    gets its own serial namespace. This prevents data_hash collisions
    on UVerify when multiple students run the same code.

    When RUN_ID is set in the environment, it is appended to the suffix
    so that each test run produces unique data_hashes — avoiding stale
    UTXO references when re-emitting credentials from the same wallet.

    Returns "000000" when no mnemonic is available (e.g. in tests
    without a configured wallet).
    """
    mnemonic = (env or {}).get("WALLET_MNEMONIC", "").strip()
    run_id = (env or {}).get("RUN_ID", "").strip()
    run_id = run_id[:4]  # cap at 4 chars to stay within 64-byte metadata limit
    if not mnemonic:
        return "000000"
    base = sha256(mnemonic.encode("utf-8")).hexdigest()[:6]
    if run_id:
        return f"{base}-{run_id}"
    return base


# ── Base serial prefixes and GTINs ────────────────────────────────
# GTINs identify the product *type* and stay fixed.
# Serial prefixes get a student-specific suffix appended at runtime.

_GTIN_ORIGEM = "7891234560099"
_GTIN_CELULA = "7891234560105"
_GTIN_PACK   = "7891234560112"
_GTIN_RECICL = "7891234560129"

_SERIAL_BASE_ORIGEM = "ML-JQT-2026-05"
_SERIAL_BASE_CELULA = "CT-BA-2026-05"
_SERIAL_BASE_PACK   = "PM-SP-2026-05"
_SERIAL_BASE_RECICL = "RL-SR-2031-09"


def _exigir(env: dict[str, str], chave: str) -> str:
    """Exige que uma variavel de ambiente esteja definida.

    Usada para validar que os tx_hashes dos atores anteriores
    (ATOR1_TX, ATOR2_TX, etc) estao preenchidos no .env antes
    de tentar emitir o proximo ator da cadeia.

    Parametros:
        env:   dicionario com variaveis de ambiente (os.environ)
        chave: nome da variavel (ex: "ATOR1_TX")

    Retorna:
        O valor da variavel (string).

    Encerra o programa com erro se a variavel estiver vazia.
    """
    valor = env.get(chave, "").strip()
    if not valor:
        sys.exit(f"ERRO: defina {chave} no .env antes de rodar este ator.")
    return valor


def _hash_serial(serial: str) -> str:
    """Calcula sha256(serial) — usado no campo uv_url_serial.

    Este hash e usado pelo UVerify para gerar a URL de verificacao
    publica do produto (ex: https://app.preprod.uverify.io/verify/...).
    """
    return sha256(serial.encode("utf-8")).hexdigest()


def data_hash(gtin: str, serial: str) -> str:
    """Calcula o hash de identificacao do produto: sha256(gtin + serial).

    Este e o `data_hash` usado pelo UVerify para indexar e buscar
    certificados. E o identificador unico do produto na blockchain.

    Exemplo:
        data_hash("7891234560099", "ML-JQT-2026-05-a1b2c3")
        → sha256 hex digest
    """
    return sha256((gtin + serial).encode("utf-8")).hexdigest()


# =====================================================================
# Ator 1 — MineraLitio (origem do litio)
#
# Primeiro elo da cadeia. Nao referencia nenhum ator anterior.
# Representa a extracao de litio no Vale do Jequitinhonha (MG, Brasil).
# =====================================================================

def payload_origem(env: dict[str, str] | None = None) -> tuple[dict, str, str]:
    """Retorna o payload DPP do Ator 1 (MineraLitio — origem do litio).

    Este e o primeiro ator da cadeia, entao nao referencia nenhuma
    credencial anterior (sem campos ref_*_tx).

    Retorna:
        Tupla (payload_dict, serial, gtin).
    """
    sid = _student_id(env)
    serial = f"{_SERIAL_BASE_ORIGEM}-{sid}"
    gtin = _GTIN_ORIGEM
    payload = {
        # Identificacao do template UVerify.
        "uverify_template_id": "digitalProductPassport",
        # Impede sobrescrita do certificado (padrao UVerify para DPP).
        "uverify_update_policy": "restricted",
        # Dados do produto.
        "name": "Lote Litio Jequitinhonha 2026-05",
        "issuer": "MineraLitio Jequitinhonha Ltda.",
        "gtin": gtin,
        "uv_url_serial": _hash_serial(serial),
        "origin": "Aracuai, Vale do Jequitinhonha, MG, BR",
        "manufactured": "2026-03-13",
        "contact": "rastreabilidade@mineralitio.example.br",
        # Sustentabilidade.
        "carbon_footprint": "4.2 kg CO2e / kg Li2CO3",
        "recycled_content": "0%",
        # Composicao de materiais (campos mat_*).
        "mat_litio_carbonato": "98%",
        "mat_impurezas_ferro": "0.3%",
        "mat_impurezas_sodio": "0.8%",
        # Certificacoes (note: esses cert_* NAO comecam com ref_,
        # entao o parser os ignora como referencias — sao apenas
        # labels informativos de certificacoes reais).
        "cert_esg_iso14001": "ISO 14001:2015",
        "cert_licenca_ambiental": "SUPRAM-JQT-LI-042-2024",
    }
    return payload, serial, gtin


# =====================================================================
# Ator 2 — CellTech (fabricacao de celulas)
#
# Segundo elo. Referencia o Ator 1 (origem do litio) via:
#   - ref_origem_tx: tx_hash da credencial do Ator 1
#   - ref_origem_data_hash: sha256(gtin+serial) do Ator 1
# =====================================================================

def payload_celula(env: dict[str, str]) -> tuple[dict, str, str]:
    """Retorna o payload DPP do Ator 2 (CellTech — celulas NMC 811).

    Referencia o Ator 1 (origem) para rastreabilidade. Os campos
    ref_origem_tx e ref_origem_data_hash permitem ao verificador
    seguir a cadeia ate a origem do litio.

    Parametros:
        env: variaveis de ambiente (precisa de ATOR1_TX).

    Retorna:
        Tupla (payload_dict, serial, gtin).
    """
    sid = _student_id(env)
    serial = f"{_SERIAL_BASE_CELULA}-{sid}"
    gtin = _GTIN_CELULA
    serial_origem = f"{_SERIAL_BASE_ORIGEM}-{sid}"
    payload = {
        "uverify_template_id": "digitalProductPassport",
        "uverify_update_policy": "restricted",
        "name": f"Celulas NMC 811 - Lote BA-2026-05-{sid}",
        "issuer": "CellTech Brasil S.A.",
        "gtin": gtin,
        "uv_url_serial": _hash_serial(serial),
        "origin": "Camacari, BA, BR",
        "manufactured": "2026-05-08",
        "contact": "qualidade@celltech.example.br",
        "carbon_footprint": "68 kg CO2e / kWh",
        "recycled_content": "4%",
        "energy_class": "NMC 811 - 270 Wh/kg",
        "warranty": "8 anos / 160.000 km no veiculo final",
        # Composicao.
        "mat_niquel": "80%",
        "mat_manganes": "10%",
        "mat_cobalto": "10%",
        "mat_litio_origem": "MineraLitio Jequitinhonha",
        # Certificacoes.
        "cert_iso9001": "ISO 9001:2015",
        "cert_iatf16949": "IATF 16949:2016",
        # Referencia ao Ator 1 (origem do litio):
        # tx_hash da credencial + data_hash para lookup UVerify.
        "ref_origem_tx": _exigir(env, "ATOR1_TX"),
        "ref_origem_data_hash": data_hash(_GTIN_ORIGEM, serial_origem),
    }
    return payload, serial, gtin


# =====================================================================
# Ator 3 — PackMontadora (montagem do pack de bateria)
#
# Terceiro elo. Referencia o Ator 2 (celulas) via:
#   - ref_celula_tx: tx_hash da credencial do Ator 2
#   - ref_celula_data_hash: sha256(gtin+serial) do Ator 2
# =====================================================================

def payload_pack(env: dict[str, str]) -> tuple[dict, str, str]:
    """Retorna o payload DPP do Ator 3 (PackMontadora — pack 75kWh).

    Referencia o Ator 2 (celulas). Este e o ponto de entrada do
    verificador — o regulador europeu escaneia o QR do pack e o
    verificador caminha para tras ate a origem.

    Parametros:
        env: variaveis de ambiente (precisa de ATOR2_TX).

    Retorna:
        Tupla (payload_dict, serial, gtin).
    """
    sid = _student_id(env)
    serial = f"{_SERIAL_BASE_PACK}-{sid}"
    gtin = _GTIN_PACK
    serial_celula = f"{_SERIAL_BASE_CELULA}-{sid}"
    payload = {
        "uverify_template_id": "digitalProductPassport",
        "uverify_update_policy": "restricted",
        "name": f"Pack EV 75kWh - SP-2026-05-{sid}",
        "issuer": "PackMontadora SP Ltda.",
        "gtin": gtin,
        "uv_url_serial": _hash_serial(serial),
        "origin": "Sao Bernardo do Campo, SP, BR",
        "manufactured": "2026-05-22",
        "contact": "pcp@packmontadora.example.br",
        "carbon_footprint": "72 kg CO2e / kWh (cradle-to-gate)",
        "recycled_content": "6%",
        "energy_class": "75 kWh utilizaveis / 82 kWh nominais",
        "warranty": "8 anos ou 160.000 km",
        "spare_parts": "Modulos individuais disponiveis ate 2038",
        # Composicao.
        "mat_celulas": "88%",
        "mat_bms": "3%",
        "mat_carcaca_aluminio": "7%",
        "mat_cabos_cobre": "2%",
        # Certificacoes de transporte e seguranca.
        "cert_un38_3": "UN 38.3 - transporte",
        "cert_iec62660": "IEC 62660-2/3",
        # Referencia ao Ator 2 (celulas):
        # tx_hash da credencial + data_hash para lookup UVerify.
        "ref_celula_tx": _exigir(env, "ATOR2_TX"),
        "ref_celula_data_hash": data_hash(_GTIN_CELULA, serial_celula),
    }
    return payload, serial, gtin


# =====================================================================
# Ator 4 — RecicLar (reciclagem do pack no fim da vida util)
#
# Quarto elo. Referencia todos os tres atores anteriores para
# rastreabilidade completa da cadeia reversa.
# =====================================================================

def payload_reciclagem(env: dict[str, str]) -> tuple[dict, str, str]:
    """Retorna o payload DPP do Ator 4 (RecicLar — reciclagem).

    Referencia os Atores 1, 2 e 3 para rastreabilidade completa
    da cadeia reversa (logistica reversa / reciclagem).

    Parametros:
        env: variaveis de ambiente (precisa de ATOR1_TX, ATOR2_TX, ATOR3_TX).

    Retorna:
        Tupla (payload_dict, serial, gtin).
    """
    sid = _student_id(env)
    serial = f"{_SERIAL_BASE_RECICL}-{sid}"
    gtin = _GTIN_RECICL
    serial_origem = f"{_SERIAL_BASE_ORIGEM}-{sid}"
    serial_celula = f"{_SERIAL_BASE_CELULA}-{sid}"
    serial_pack = f"{_SERIAL_BASE_PACK}-{sid}"
    payload = {
        "uverify_template_id": "digitalProductPassport",
        "uverify_update_policy": "restricted",
        "name": f"Reciclagem Pack 75kWh - SR-2031-09-{sid}",
        "issuer": "RecicLar Sorocaba S.A.",
        "gtin": gtin,
        "uv_url_serial": _hash_serial(serial),
        "origin": "Sorocaba, SP, BR",
        "manufactured": "2031-09-17",
        "contact": "logreversa@reciclar.example.br",
        "recycled_content": "N/A (processo de reciclagem)",
        # Materiais recuperados na reciclagem.
        "mat_litio_recuperado": "3.8 kg",
        "mat_niquel_recuperado": "38 kg",
        "mat_cobalto_recuperado": "4.6 kg",
        "mat_cobre_recuperado": "9.2 kg",
        # Referencias a todos os atores anteriores:
        # Cada par (ref_*_tx + ref_*_data_hash) permite ao verificador
        # rastrear cada elo da cadeia.
        "ref_pack_tx": _exigir(env, "ATOR3_TX"),
        "ref_pack_data_hash": data_hash(_GTIN_PACK, serial_pack),
        "ref_celula_tx": _exigir(env, "ATOR2_TX"),
        "ref_celula_data_hash": data_hash(_GTIN_CELULA, serial_celula),
        "ref_origem_tx": _exigir(env, "ATOR1_TX"),
        "ref_origem_data_hash": data_hash(_GTIN_ORIGEM, serial_origem),
    }
    return payload, serial, gtin


# =====================================================================
# Registros de atores — usados pelos emissores para saber qual
# funcao de payload chamar e qual variavel de ambiente atualizar.
# =====================================================================

# Mapeia nome do ator → funcao que gera o payload.
ATORES: dict[str, Callable[[dict[str, str]], tuple[dict, str, str]]] = {
    "origem": payload_origem,
    "celula": payload_celula,
    "pack": payload_pack,
    "reciclagem": payload_reciclagem,
}

# Mapeia nome do ator → variavel de ambiente onde o tx_hash e salvo
# apos a emissao (auto-atualizado no .env pelos emissores).
PROXIMO_ATOR_ENV = {
    "origem": "ATOR1_TX",
    "celula": "ATOR2_TX",
    "pack": "ATOR3_TX",
    "reciclagem": "ATOR4_TX",
}
