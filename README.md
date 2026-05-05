# Verificador & Emissor DPP — Workshop Cardano

**De Jequitinhonha à Europa: o Passaporte da Bateria**

Starter project em Python 3.11+ que **emite** e **verifica** uma
cadeia de Passaportes Digitais de Produto (DPP) ancorados em
Cardano **preprod** — com **duas implementações paralelas** para
cada operação:

| Operação | Opção A (direto) | Opção B (via UVerify) |
|---|---|---|
| **Emissão** | `emissor_direto.py` — PyCardano `TransactionBuilder` + native metadata | `emissor_sdk.py` — `uverify-sdk` |
| **Verificação** | `verificador_direto.py` — Blockfrost + parser próprio | `verificador_sdk.py` — `uverify-sdk` |

> ⚠️ **Rede:** o UVerify público opera em **preprod testnet**. Todo
> o starter aponta para preprod (Blockfrost preprod, faucet preprod,
> CardanoScan preprod, API UVerify preprod).

---

## Pré-requisitos

| Componente | Versão |
|---|---|
| Python | 3.11+ |
| pip | recente |
| IDE | VS Code com Python extension, PyCharm Community ou similar |
| Carteira Cardano | [Eternl](https://eternl.io) ou [Lace](https://lace.io) em **preprod** |
| tADA | [Faucet preprod](https://docs.cardano.org/cardano-testnets/tools/faucet/) |
| Blockfrost | Conta gratuita em [blockfrost.io](https://blockfrost.io), projeto **preprod** |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# preencha BLOCKFROST_PROJECT_ID e WALLET_MNEMONIC (TESTNET ONLY)
```

## Emissão (Seção 2 do hands-on)

Antes de emitir: tenha tADA na carteira preprod cuja mnemônica está
em `WALLET_MNEMONIC`.

### Opção A — direto via PyCardano

```bash
PYTHONPATH=src python -m verificador_dpp.emissor_direto --ator origem
# cole o tx_hash em ATOR1_TX no .env, depois:
PYTHONPATH=src python -m verificador_dpp.emissor_direto --ator celula
PYTHONPATH=src python -m verificador_dpp.emissor_direto --ator pack
PYTHONPATH=src python -m verificador_dpp.emissor_direto --ator reciclagem
```

### Opção B — via UVerify SDK

```bash
PYTHONPATH=src python -m verificador_dpp.emissor_sdk --ator origem
# cole o tx_hash em ATOR1_TX no .env, depois:
PYTHONPATH=src python -m verificador_dpp.emissor_sdk --ator celula
PYTHONPATH=src python -m verificador_dpp.emissor_sdk --ator pack
PYTHONPATH=src python -m verificador_dpp.emissor_sdk --ator reciclagem
```

Os dois caminhos usam os mesmos payloads (`_payloads.py`) e a
mesma carteira HD (`wallet.py`).

## Verificação (Seção 3 do hands-on)

Pré-requisito: `TX_HASH_PACK` e `DATA_HASH_PACK` no `.env`.

### Opção A — direto via Blockfrost

```bash
PYTHONPATH=src python -m verificador_dpp.verificador_direto
# ou
PYTHONPATH=src python -m verificador_dpp.verificador_direto <txHashPack>
```

Reconstrói a cadeia origem → célula → pack seguindo as
referências `cert_*_credential_tx`.

### Opção B — via UVerify SDK

```bash
PYTHONPATH=src python -m verificador_dpp.verificador_sdk
# ou
PYTHONPATH=src python -m verificador_dpp.verificador_sdk \
    --tx <txHashPack> --hash <dataHashPack>
```

Uma única chamada HTTP devolve a credencial estruturada.

## Estrutura

```
starter/
├── requirements.txt
├── .env.example
├── README.md
└── src/verificador_dpp/
    ├── __init__.py
    ├── __main__.py            # help dispatcher
    ├── _payloads.py           # payloads DPP por ator (compartilhado)
    ├── wallet.py              # HD wallet CIP-1852 (compartilhado)
    ├── emissor_direto.py      # Opção A — PyCardano TransactionBuilder
    ├── emissor_sdk.py         # Opção B — uverify-sdk
    ├── verificador_direto.py  # Opção A — Blockfrost + parser
    ├── verificador_sdk.py     # Opção B — uverify-sdk
    ├── cliente_blockfrost.py  # wrapper Blockfrost (usado pela Opção A do verificador)
    ├── parser_credencial.py   # parse de metadata UVerify
    ├── relatorio_passaporte.py # relatório pt-BR
    └── modelos.py             # dataclasses CredencialDPP / PassaporteBateria
```

## Dependências principais

- `pycardano` (>= 0.11) — biblioteca canônica Python para Cardano
- `blockfrost-python` (>= 0.6) — cliente REST do Blockfrost
- `uverify-sdk` (>= 0.1.5) — SDK oficial do UVerify
- `python-dotenv` (>= 1.0) — carrega variáveis do `.env`
- `cbor2 < 6` — pin necessário até o `cbor2pure` suportar a 6.x

## Troubleshooting

Veja a Seção 6 do guia hands-on (`02-mao-na-massa.md`).
