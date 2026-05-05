"""Payloads DPP por ator.

Usados pelos dois emissores (direto e via SDK). Os campos seguem o
template `digitalProductPassport`
(https://docs.uverify.io/templates/built-in). Todos os valores sao
strings - exigencia do CertificateData.metadata: Dict[str, str].
"""

from __future__ import annotations

import sys
from hashlib import sha256
from typing import Callable


def _exigir(env: dict[str, str], chave: str) -> str:
    valor = env.get(chave, "").strip()
    if not valor:
        sys.exit(f"ERRO: defina {chave} no .env antes de rodar este ator.")
    return valor


def _hash_serial(serial: str) -> str:
    return sha256(serial.encode("utf-8")).hexdigest()


def data_hash(gtin: str, serial: str) -> str:
    """Hash de identificacao do produto - sha256(gtin + serial)."""
    return sha256((gtin + serial).encode("utf-8")).hexdigest()


# -----------------------------------------------------------------
# Ator 1 - MineraLitio (origem do litio)
# -----------------------------------------------------------------

def payload_origem(_env: dict[str, str] | None = None) -> tuple[dict, str, str]:
    serial = "ML-JQT-2026-03-042"
    gtin = "7891234560013"
    payload = {
        "uverify_template_id": "digitalProductPassport",
        "name": "Lote Litio Jequitinhonha 2026-03",
        "issuer": "MineraLitio Jequitinhonha Ltda.",
        "gtin": gtin,
        "uv_url_serial": _hash_serial(serial),
        "origin": "Aracuai, Vale do Jequitinhonha, MG, BR",
        "manufactured": "2026-03-13",
        "contact": "rastreabilidade@mineralitio.example.br",
        "carbon_footprint": "4.2 kg CO2e / kg Li2CO3",
        "recycled_content": "0%",
        "mat_litio_carbonato": "98%",
        "mat_impurezas_ferro": "0.3%",
        "mat_impurezas_sodio": "0.8%",
        "cert_esg_iso14001": "ISO 14001:2015",
        "cert_licenca_ambiental": "SUPRAM-JQT-LI-042-2024",
    }
    return payload, serial, gtin


# -----------------------------------------------------------------
# Ator 2 - CellTech (celulas, referencia origem)
# -----------------------------------------------------------------

def payload_celula(env: dict[str, str]) -> tuple[dict, str, str]:
    serial = "CT-BA-2026-04-008"
    gtin = "7891234560020"
    payload = {
        "uverify_template_id": "digitalProductPassport",
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
        "mat_niquel": "80%",
        "mat_manganes": "10%",
        "mat_cobalto": "10%",
        "mat_litio_origem": "MineraLitio Jequitinhonha",
        "cert_iso9001": "ISO 9001:2015",
        "cert_iatf16949": "IATF 16949:2016",
        "cert_origem_credential_tx": _exigir(env, "ATOR1_TX"),
    }
    return payload, serial, gtin


# -----------------------------------------------------------------
# Ator 3 - PackMontadora (pack, referencia celula)
# -----------------------------------------------------------------

def payload_pack(env: dict[str, str]) -> tuple[dict, str, str]:
    serial = "PM-SP-2026-04-155"
    gtin = "7891234560037"
    payload = {
        "uverify_template_id": "digitalProductPassport",
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
        "mat_celulas": "88%",
        "mat_bms": "3%",
        "mat_carcaca_aluminio": "7%",
        "mat_cabos_cobre": "2%",
        "cert_un38_3": "UN 38.3 - transporte",
        "cert_iec62660": "IEC 62660-2/3",
        "cert_celula_credential_tx": _exigir(env, "ATOR2_TX"),
    }
    return payload, serial, gtin


# -----------------------------------------------------------------
# Ator 4 - RecicLar (reciclagem, referencia pack/celula/origem)
# -----------------------------------------------------------------

def payload_reciclagem(env: dict[str, str]) -> tuple[dict, str, str]:
    serial = "RL-SR-2031-08-001"
    gtin = "7891234560044"
    payload = {
        "uverify_template_id": "digitalProductPassport",
        "name": "Reciclagem Pack 75kWh - SR-2031-08-001",
        "issuer": "RecicLar Sorocaba S.A.",
        "gtin": gtin,
        "uv_url_serial": _hash_serial(serial),
        "origin": "Sorocaba, SP, BR",
        "manufactured": "2031-08-17",
        "contact": "logreversa@reciclar.example.br",
        "recycled_content": "N/A (processo de reciclagem)",
        "mat_litio_recuperado": "3.8 kg",
        "mat_niquel_recuperado": "38 kg",
        "mat_cobalto_recuperado": "4.6 kg",
        "mat_cobre_recuperado": "9.2 kg",
        "cert_pack_credential_tx": _exigir(env, "ATOR3_TX"),
        "cert_celula_credential_tx": _exigir(env, "ATOR2_TX"),
        "cert_origem_credential_tx": _exigir(env, "ATOR1_TX"),
    }
    return payload, serial, gtin


ATORES: dict[str, Callable[[dict[str, str]], tuple[dict, str, str]]] = {
    "origem": payload_origem,
    "celula": payload_celula,
    "pack": payload_pack,
    "reciclagem": payload_reciclagem,
}

PROXIMO_ATOR_ENV = {
    "origem": "ATOR1_TX",
    "celula": "ATOR2_TX",
    "pack": "ATOR3_TX",
    "reciclagem": "ATOR4_TX",
}
