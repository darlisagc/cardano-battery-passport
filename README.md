# DPP Workshop Cardano

**De Jequitinhonha a Europa: o Passaporte da Bateria**

This repository implements a **Digital Product Passport (DPP)** for electric vehicle batteries, anchored on the **Cardano blockchain** (preprod testnet). The use case tracks a battery's full supply chain — from **lithium extraction** in Jequitinhonha Valley (Minas Gerais, Brazil), through **cell manufacturing** in Camacari (Bahia), **pack assembly** in Sao Bernardo do Campo (Sao Paulo), and finally **recycling** in Sorocaba (Sao Paulo). Each step in this chain is recorded as an on-chain credential that references the previous one, creating an immutable, verifiable trail from raw material to end-of-life.

The four actors in the supply chain are:

| Actor | Company | Role |
|-------|---------|------|
| **Ator 1** | MineraLitio Jequitinhonha | Lithium extraction (raw material) |
| **Ator 2** | CellTech Brasil | NMC 811 cell manufacturing |
| **Ator 3** | PackMontadora SP | 75 kWh battery pack assembly |
| **Ator 4** | RecicLar Sorocaba | End-of-life recycling |

Each actor **emits** a credential containing product data (GTIN, origin, carbon footprint, material composition) and a reference (`ref_*_tx`) pointing to the previous actor's transaction. The **verificador** then walks this chain backwards — from the pack (or recycling) credential all the way to the lithium origin — to reconstruct and validate the complete passport.

> **Network:** everything runs on **Cardano preprod testnet** — Blockfrost preprod, tADA faucet, Cexplorer preprod, UVerify preprod API. No real ADA is used.

---

## Prerequisites

| Component | Description |
|-----------|-------------|
| Python | 3.11 or higher |
| [uv](https://docs.astral.sh/uv/) | Package/venv manager — install with `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| IDE | VS Code with Python extension, PyCharm Community, or similar |
| Cardano wallet | [Eternl](https://eternl.io) or [Lace](https://lace.io) set to **preprod** |
| tADA | Get test ADA from the [preprod faucet](https://docs.cardano.org/cardano-testnets/tools/faucet/) |
| Blockfrost | Free account at [blockfrost.io](https://blockfrost.io) — create a **preprod** project |

## Setup

```bash
uv sync                  # creates .venv and installs all dependencies (reproducible via uv.lock)
cp .env.example .env     # fill in BLOCKFROST_PROJECT_ID and WALLET_MNEMONIC (TESTNET ONLY)
```

`uv sync` is idempotent — run it as many times as you want. You don't need to activate the venv manually: just use `uv run <command>` from anywhere in the project and `uv` handles the environment.

## Emission

Before emitting, make sure you have tADA in the preprod wallet whose mnemonic is in `WALLET_MNEMONIC`.

There are **three ways** to emit credentials. All three produce on-chain credentials that the verificador can read:

### Option A — Native metadata via PyCardano (`emissor_direto`)

Builds a Cardano transaction directly using PyCardano's `TransactionBuilder`, attaching the DPP payload as **native transaction metadata** (label 721). The credential data is written directly into the transaction — no smart contract involved.

```bash
uv run python -m verificador_dpp.emissor_direto --ator origem
uv run python -m verificador_dpp.emissor_direto --ator celula
uv run python -m verificador_dpp.emissor_direto --ator pack
uv run python -m verificador_dpp.emissor_direto --ator reciclagem
```

Each command prints the tx hash and automatically updates the `.env` file (`ATOR1_TX`, `ATOR2_TX`, etc.) so the next actor can reference it.

### Option B — UVerify SDK (`emissor_sdk`)

Emits through the [UVerify](https://uverify.io) platform, which uses **Plutus V3 smart contracts** to anchor the credential. The SDK handles the smart contract interaction (building the Plutus transaction, managing state datums, submitting to chain). The emission module includes robust error handling for the preprod environment.

```bash
uv run python -m verificador_dpp.emissor_sdk --ator origem
uv run python -m verificador_dpp.emissor_sdk --ator celula
uv run python -m verificador_dpp.emissor_sdk --ator pack
uv run python -m verificador_dpp.emissor_sdk --ator reciclagem
```

Same `.env` auto-update behavior as Option A.

### Option C — UVerify web UI (no code)

1. Open <https://app.preprod.uverify.io> and connect your preprod wallet.
2. **Issue Certificate** → select the **Digital Product Passport** template.
3. Fill in the payload fields for the actor (see `_payloads.py` for reference). For actors 2-4, set `ref_*_tx` to the previous actor's tx hash.
4. **Issue** → sign in your wallet → copy the tx hash to `.env` as `ATOR<N>_TX=...`.

### Mixing modes

You can freely mix options A, B, and C within the same supply chain. For example, emit `origem` via direto (A), `celula` via SDK (B), and `pack` via the web UI (C). The verificador handles any combination.

## Verification

```bash
uv run python -m verificador_dpp.verificador              # reads TX_HASH_PACK from .env
uv run python -m verificador_dpp.verificador <tx_hash>    # or pass a tx hash directly
```

The verificador walks the credential chain regardless of which emission option was used. Starting from the pack (or recycling) credential, it follows `ref_*_tx` references backwards through the chain — pack → celula → origem — and outputs a consolidated passport with all product data, carbon footprint, and material composition.

For quick single-credential checks via browser (useful for demos or QR-code scanning):

```
https://app.preprod.uverify.io/verify/<DATA_HASH>
```

This only works for credentials emitted via UVerify (B or C) and doesn't reconstruct the full chain.

## Project structure

```
cardano-battery-passport/
├── pyproject.toml                          # Project config and dependencies
├── uv.lock                                 # Pinned dependency versions for reproducible builds
├── .env.example                            # Template — copy to .env and fill in your keys
├── README.md
├── mao-na-massa.md                         # Step-by-step hands-on guide (pt-BR, 180 min workshop)
├── arquitetura-dpp.md                      # Architecture deep-dive and design decisions
└── src/verificador_dpp/
    ├── __init__.py
    ├── __main__.py                         # Help dispatcher — shows available commands
    ├── _payloads.py                        # DPP payloads for all 4 actors (shared by A and B)
    ├── _html_utils.py                      # HTML escape and Cexplorer link helpers
    ├── wallet.py                           # HD wallet derivation (CIP-1852) from mnemonic
    ├── emissor_direto.py                   # Option A — builds and submits tx via PyCardano
    ├── emissor_sdk.py                      # Option B — emits via UVerify SDK (Plutus V3)
    ├── verificador.py                      # Reads and walks the credential chain (covers A+B+C)
    ├── parser_credencial.py                # Parses Blockfrost metadata into CredencialDPP objects
    ├── modelos.py                          # Data classes: CredencialDPP, PassaporteBateria
    ├── relatorio_passaporte.py             # Text report (pt-BR terminal output)
    ├── relatorio_html.py                   # HTML report — full supply chain passport
    ├── relatorio_emissao_html.py           # HTML receipt generated after each emission
    └── relatorio_reciclagem_html.py        # HTML report for recycling (Actor 4)
```

### What each file does

**Core modules:**

- **`_payloads.py`** — Defines the DPP data for all 4 actors. Each payload is a dictionary of key-value pairs (product name, GTIN, origin, carbon footprint, materials, and references to previous actors). Both emission options A and B use the same payloads, ensuring identical on-chain data regardless of the emission method.

- **`wallet.py`** — Derives a payment signing key and a preprod address from a 24-word BIP-39 mnemonic using the CIP-1852 HD derivation standard. The resulting address matches what you see in Eternl or Lace. Shared by both emitters.

- **`emissor_direto.py`** (Option A) — Builds a Cardano transaction with PyCardano's `TransactionBuilder`, attaches the DPP payload as native metadata (label 721), signs it with the wallet key, and submits to the network via Blockfrost. Straightforward and fast — no smart contract involved.

- **`emissor_sdk.py`** (Option B) — Emits through the UVerify SDK, which interacts with Plutus V3 smart contracts on preprod. Includes robust handling for state datum cleanup, collateral UTXO preparation, status code interpretation, CIP-8 message signing, and exponential backoff retry. See the inline code comments for implementation details.

- **`verificador.py`** — The unified verifier. Given a tx hash, it fetches the credential from chain (trying native metadata first, then UVerify API), reads the `ref_*_tx` references, and recursively walks the chain until it reaches the origin. Works with any mix of emission methods. Outputs a consolidated passport to the terminal and generates an HTML report.

**Data and parsing:**

- **`modelos.py`** — Defines `CredencialDPP` (a single credential with product data, materials, and chain references) and `PassaporteBateria` (groups origin + celula + pack + optional recycling into one passport).

- **`parser_credencial.py`** — Converts raw Blockfrost metadata (which comes as nested Namespace objects) into structured `CredencialDPP` objects. Handles the `digitalProductPassport` template format and classifies fields by prefix (`ref_*`, `mat_*`, `uv_*`).

**Reports:**

- **`relatorio_passaporte.py`** — Generates the text-based passport report printed to the terminal after verification.
- **`relatorio_html.py`** — Generates an HTML report with colored cards for each supply chain step (green=origin, blue=cells, yellow=pack, teal=recycling).
- **`relatorio_emissao_html.py`** — Generates an HTML receipt after each individual emission, with a Cexplorer link to the transaction.
- **`relatorio_reciclagem_html.py`** — Generates a dedicated HTML report for the recycling credential (Actor 4).
- **`_html_utils.py`** — Shared helpers: HTML escaping and Cexplorer preprod link generation.

## Dependencies

| Package | Purpose |
|---------|---------|
| `pycardano` (>= 0.11) | Python library for Cardano — builds, signs, and submits transactions |
| `blockfrost-python` (>= 0.6) | REST client for the Blockfrost API (blockchain data access) |
| `uverify-sdk` (>= 0.1.8) | Official UVerify SDK for certificate issuance and verification |
| `python-dotenv` (>= 1.0) | Loads environment variables from `.env` |
| `cbor2 < 6` | CBOR decoder (Cardano's binary serialization format); pinned below 6 until `cbor2pure` support lands |

Exact versions are pinned in `uv.lock` (committed for reproducible builds).

## Troubleshooting

For detailed troubleshooting, error messages, and step-by-step debugging guidance, see **Section 5** of the hands-on guide: [`mao-na-massa.md`](mao-na-massa.md).
