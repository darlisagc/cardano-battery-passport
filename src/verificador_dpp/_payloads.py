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
    campos cert_*_credential_tx (tx_hash da tx anterior)
    Analogia: como links que permitem ao verificador "caminhar" pela
    cadeia de certificados, do produto final ate a materia-prima.
  - Data hashes (impressoes digitais SHA-256): campos cert_*_data_hash
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
        data_hash("7891234560013", "ML-JQT-2026-03-042")
        → "b23525533242f8ba2ae0435170dd99c8bf1a706f261c0062aac827485a3537b0"
    """
    return sha256((gtin + serial).encode("utf-8")).hexdigest()


# =====================================================================
# Ator 1 — MineraLitio (origem do litio)
#
# Primeiro elo da cadeia. Nao referencia nenhum ator anterior.
# Representa a extracao de litio no Vale do Jequitinhonha (MG, Brasil).
# =====================================================================

def payload_origem(_env: dict[str, str] | None = None) -> tuple[dict, str, str]:
    """Retorna o payload DPP do Ator 1 (MineraLitio — origem do litio).

    Este e o primeiro ator da cadeia, entao nao referencia nenhuma
    credencial anterior (sem campos cert_*_credential_tx).

    Retorna:
        Tupla (payload_dict, serial, gtin).
    """
    serial = "ML-JQT-2026-03-042"
    gtin = "7891234560013"
    payload = {
        # Identificacao do template UVerify.
        "uverify_template_id": "digitalProductPassport",
        # Impede sobrescrita do certificado (padrao UVerify para DPP).
        "uverify_update_policy": "restricted",
        # Dados do produto.
        "name": "Lote Litio Jequitinhonha 2026-03",
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
        # Certificacoes (note: esses cert_* NAO terminam em
        # _credential_tx nem _data_hash, entao o parser os ignora
        # como referencias — sao apenas labels informativos).
        "cert_esg_iso14001": "ISO 14001:2015",
        "cert_licenca_ambiental": "SUPRAM-JQT-LI-042-2024",
    }
    return payload, serial, gtin


# =====================================================================
# Ator 2 — CellTech (fabricacao de celulas)
#
# Segundo elo. Referencia o Ator 1 (origem do litio) via:
#   - cert_origem_credential_tx: tx_hash da credencial do Ator 1
#   - cert_origem_data_hash: sha256(gtin+serial) do Ator 1
# =====================================================================

def payload_celula(env: dict[str, str]) -> tuple[dict, str, str]:
    """Retorna o payload DPP do Ator 2 (CellTech — celulas NMC 811).

    Referencia o Ator 1 (origem) para rastreabilidade. Os campos
    cert_origem_credential_tx e cert_origem_data_hash permitem ao
    verificador seguir a cadeia ate a origem do litio.

    Parametros:
        env: variaveis de ambiente (precisa de ATOR1_TX).

    Retorna:
        Tupla (payload_dict, serial, gtin).
    """
    serial = "CT-BA-2026-04-008"
    gtin = "7891234560020"
    payload = {
        "uverify_template_id": "digitalProductPassport",
        "uverify_update_policy": "restricted",
        "name": "Celulas NMC 811 - Lote BA-2026-04-008",
        "issuer": "CellTech Brasil S.A.",
        "gtin": gtin,
        "uv_url_serial": _hash_serial(serial),
        "origin": "Camacari, BA, BR",
        "manufactured": "2026-04-08",
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
        "cert_origem_credential_tx": _exigir(env, "ATOR1_TX"),
        "cert_origem_data_hash": data_hash("7891234560013", "ML-JQT-2026-03-042"),
    }
    return payload, serial, gtin


# =====================================================================
# Ator 3 — PackMontadora (montagem do pack de bateria)
#
# Terceiro elo. Referencia o Ator 2 (celulas) via:
#   - cert_celula_credential_tx: tx_hash da credencial do Ator 2
#   - cert_celula_data_hash: sha256(gtin+serial) do Ator 2
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
    serial = "PM-SP-2026-04-155"
    gtin = "7891234560037"
    payload = {
        "uverify_template_id": "digitalProductPassport",
        "uverify_update_policy": "restricted",
        "name": "Pack EV 75kWh - SP-2026-04-155",
        "issuer": "PackMontadora SP Ltda.",
        "gtin": gtin,
        "uv_url_serial": _hash_serial(serial),
        "origin": "Sao Bernardo do Campo, SP, BR",
        "manufactured": "2026-04-22",
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
        "cert_celula_credential_tx": _exigir(env, "ATOR2_TX"),
        "cert_celula_data_hash": data_hash("7891234560020", "CT-BA-2026-04-008"),
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
    serial = "RL-SR-2031-08-001"
    gtin = "7891234560044"
    payload = {
        "uverify_template_id": "digitalProductPassport",
        "uverify_update_policy": "restricted",
        "name": "Reciclagem Pack 75kWh - SR-2031-08-001",
        "issuer": "RecicLar Sorocaba S.A.",
        "gtin": gtin,
        "uv_url_serial": _hash_serial(serial),
        "origin": "Sorocaba, SP, BR",
        "manufactured": "2031-08-17",
        "contact": "logreversa@reciclar.example.br",
        "recycled_content": "N/A (processo de reciclagem)",
        # Materiais recuperados na reciclagem.
        "mat_litio_recuperado": "3.8 kg",
        "mat_niquel_recuperado": "38 kg",
        "mat_cobalto_recuperado": "4.6 kg",
        "mat_cobre_recuperado": "9.2 kg",
        # Referencias a todos os atores anteriores:
        # Cada par (credential_tx + data_hash) permite ao verificador
        # rastrear cada elo da cadeia.
        "cert_pack_credential_tx": _exigir(env, "ATOR3_TX"),
        "cert_pack_data_hash": data_hash("7891234560037", "PM-SP-2026-04-155"),
        "cert_celula_credential_tx": _exigir(env, "ATOR2_TX"),
        "cert_celula_data_hash": data_hash("7891234560020", "CT-BA-2026-04-008"),
        "cert_origem_credential_tx": _exigir(env, "ATOR1_TX"),
        "cert_origem_data_hash": data_hash("7891234560013", "ML-JQT-2026-03-042"),
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
