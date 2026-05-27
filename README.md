#  DPP Workshop Cardano

**De Jequitinhonha à Europa: o Passaporte da Bateria**

Starter project em Python 3.11+ que **emite** e **verifica** uma
cadeia de Passaportes Digitais de Produto (DPP) ancorados em
Cardano **preprod** — com **duas implementações paralelas** para
cada operação:

**Emissão** tem três opções (A, B, C); **verificação** é unificada num único módulo que cobre qualquer mistura:

| Emissão | Como | Verificação (única) |
|---|---|---|
| **A — Python direto** | `emissor_direto.py` (PyCardano `TransactionBuilder`) | `verificador.py` |
| **B — Python via SDK** | `emissor_sdk.py` (`uverify-sdk`) | `verificador.py` |
| **C — UI UVerify** | <https://app.preprod.uverify.io> (sem código) | `verificador.py` |

> ⚠️ **Rede:** o UVerify público opera em **preprod testnet**. Todo
> o starter aponta para preprod (Blockfrost preprod, faucet preprod,
> Cexplorer preprod, API UVerify preprod).

---

## Pré-requisitos

| Componente | Versão |
|---|---|
| Python | 3.11+ |
| [uv](https://docs.astral.sh/uv/) | gerenciador de pacotes/venv (instale com `curl -LsSf https://astral.sh/uv/install.sh \| sh`) |
| IDE | VS Code com Python extension, PyCharm Community ou similar |
| Carteira Cardano | [Eternl](https://eternl.io) ou [Lace](https://lace.io) em **preprod** |
| tADA | [Faucet preprod](https://docs.cardano.org/cardano-testnets/tools/faucet/) |
| Blockfrost | Conta gratuita em [blockfrost.io](https://blockfrost.io), projeto **preprod** |

## Setup

```bash
uv sync                  # cria .venv e instala dependencias com lock reproducivel
cp .env.example .env     # preencha BLOCKFROST_PROJECT_ID e WALLET_MNEMONIC (TESTNET ONLY)
```

`uv sync` é idempotente — roda quantas vezes quiser. Não precisa
ativar o venv: use `uv run <comando>` em qualquer diretório do
projeto e o uv resolve tudo.

## Emissão (Seção 2 do hands-on)

Antes de emitir: tenha tADA na carteira preprod cuja mnemônica está
em `WALLET_MNEMONIC`.

### Opção A — direto via PyCardano

```bash
uv run python -m verificador_dpp.emissor_direto --ator origem
# o tx_hash vai automaticamente para ATOR1_TX no .env, depois:
uv run python -m verificador_dpp.emissor_direto --ator celula
uv run python -m verificador_dpp.emissor_direto --ator pack
uv run python -m verificador_dpp.emissor_direto --ator reciclagem
```

### Opção B — via UVerify SDK

```bash
uv run python -m verificador_dpp.emissor_sdk --ator origem
# o tx_hash vai automaticamente para ATOR1_TX no .env, depois:
uv run python -m verificador_dpp.emissor_sdk --ator celula
uv run python -m verificador_dpp.emissor_sdk --ator pack
uv run python -m verificador_dpp.emissor_sdk --ator reciclagem
```

O `emissor_sdk` implementa um fluxo robusto de emissão com **5 camadas
de proteção**, necessárias porque o UVerify usa smart contracts Plutus V3
na preprod:

1. **Verificação de estado** — detecta e invalida State Datums obsoletos
   (Bug #54 do UVerify) que causam erros `/ by zero` no backend.
2. **Preparação de colateral** — garante um UTXO de ≥5 ADA dedicado
   para execução de scripts Plutus (exigência do protocolo Cardano).
3. **Tratamento de status codes** — interpreta `COLLATERAL_REQUIRED` e
   `PENDING_TRANSACTION` na resposta do build e age automaticamente.
4. **Exponential backoff** — 5 tentativas com delays progressivos
   (5s → 10s → 20s → 40s → 80s) para erros transientes da API.
5. **Detecção de carteira vazia** — aborta imediatamente se não houver
   UTXOs (sem sentido retentear).

Os dois caminhos Python (A e B) usam os mesmos payloads (`_payloads.py`)
e a mesma carteira HD (`wallet.py`). Cada payload que referencia outro
ator inclui tanto `ref_*_tx` (tx hash) quanto `ref_*_data_hash`
(`sha256(gtin+serial)`) — o verificador usa ambos para caminhar a cadeia
independente do método de emissão.

### Opção C — via UI UVerify (sem código)

1. Abra <https://app.preprod.uverify.io>, conecte a carteira preprod.
2. *Issue Certificate* → template **Digital Product Passport**.
3. Cole os campos do payload do ator (referência: `_payloads.py` ou
   Seção 2.2 do hands-on). Para atores 2-4, preencha
   `ref_*_tx` com os tx hashes anteriores.
4. **Issue** → assine na carteira → copie o tx hash para o `.env`
   como `ATOR<N>_TX=…`.

## Verificação (Seção 3 do hands-on)

Pré-requisitos no `.env`: `TX_HASH_PACK` e — se algum ator foi
emitido via UVerify (B ou C) — `DATA_HASH_PACK`.

```bash
uv run python -m verificador_dpp.verificador
# ou:
uv run python -m verificador_dpp.verificador <txHashPack>
```

`verificador` caminha qualquer cadeia, independente de qual
opção emitiu cada credencial. Para cada tx:

1. Tenta a **metadata nativa Cardano** via Blockfrost — funciona se
   foi emitida pelo `emissor_direto`. Analogia: lê o "anexo" da
   transação onde os dados do certificado estão gravados.
2. Se não achar `uverify_template_id`, reúne candidatos a
   `data_hash` (impressão digital do produto) de três fontes:
   - **Hint da cadeia** — campo `ref_*_data_hash` da credencial
     que referencia esta tx (como um "atalho" para o próximo).
   - **Redeemer on-chain** — extrai o hash do certificado do
     redeemer (o "comprovante" do smart contract) via Blockfrost.
   - **Inline datum** — fallback heurístico: vasculha a "ficha de
     cadastro" do smart contract procurando sequências de 32 bytes.
3. Testa cada candidato contra a API pública do UVerify via HTTP
   direto (evita `RecursionError` do SDK causado por respostas
   com histórico `stateDatum` profundamente aninhado).

Walks `ref_*_tx` + `ref_*_data_hash` references até montar o
passaporte completo (origem → célula → pack, e opcionalmente reciclagem).

### Atalho — verificação ad-hoc via URL UVerify (sem código)

Para inspecionar **uma** credencial individual via browser (útil
para demos ou para o consumidor final que só escaneia um QR):

```
https://app.preprod.uverify.io/verify/<DATA_HASH>
https://app.preprod.uverify.io/verify/<DATA_HASH>?serial=<SERIAL>
```

Funciona apenas em credenciais emitidas via UVerify (B ou C). Não
monta a cadeia — para reconstruir origem→célula→pack (→reciclagem), use
`verificador`.

## Estrutura

```
starter/
├── pyproject.toml
├── uv.lock
├── .env.example
├── README.md
└── src/verificador_dpp/
    ├── __init__.py
    ├── __main__.py              # help dispatcher
    ├── _payloads.py             # payloads DPP por ator (compartilhado)
    ├── _html_utils.py           # utilidades HTML compartilhadas (esc_html, cexplorer_link)
    ├── wallet.py                # HD wallet CIP-1852 (compartilhado)
    ├── emissor_direto.py        # Opção A — PyCardano TransactionBuilder
    ├── emissor_sdk.py           # Opção B — uverify-sdk (5-layer robust: state, collateral, retry)
    ├── verificador.py           # único verificador (cobre A + B + C)
    ├── parser_credencial.py     # parse de metadata → CredencialDPP + classificar_campos()
    ├── modelos.py               # dataclasses CredencialDPP / PassaporteBateria
    ├── relatorio_passaporte.py  # relatório texto pt-BR
    ├── relatorio_html.py        # relatório HTML da cadeia de suprimentos
    ├── relatorio_emissao_html.py      # receipt HTML de emissão individual
    └── relatorio_reciclagem_html.py   # relatório HTML de reciclagem
```

## Dependências principais

- `pycardano` (>= 0.11) — biblioteca canônica Python para Cardano (constrói, assina e submete transações)
- `blockfrost-python` (>= 0.6) — cliente REST do Blockfrost (acesso à blockchain via API)
- `uverify-sdk` (>= 0.1.8) — SDK oficial do UVerify (emissão e verificação de certificados)
- `python-dotenv` (>= 1.0) — carrega variáveis do `.env`
- `cbor2 < 6` — decodificador CBOR (formato binário de serialização usado pelo Cardano); pin necessário até o `cbor2pure` suportar a 6.x

Versões exatas ficam pinadas no `uv.lock` (commitado para builds reproduzíveis).

## Troubleshooting

- **`RecursionError` ao verificar credenciais UVerify (B/C):** a API
  UVerify pode retornar respostas com histórico `stateDatum` muito
  aninhado (centenas de níveis — como seções dentro de seções). O
  verificador contorna isso com HTTP direto em vez do SDK.
- **404 ao seguir a cadeia:** verifique que os payloads incluem
  `ref_*_data_hash` (necessário para credenciais B/C). Re-emita os
  atores com a versão atualizada de `_payloads.py`.
- **500 / `by zero` no emissor_sdk:** a carteira tem um State Datum
  obsoleto de uma era anterior do Bootstrap (Bug #54 do UVerify preprod).
  O `emissor_sdk` detecta e invalida esse estado automaticamente via
  `opt_out()`. Se persistir, crie uma carteira nova ou aguarde o fix
  server-side do UVerify.
- **`COLLATERAL_REQUIRED` ao emitir via SDK:** o UVerify usa scripts
  Plutus V3 que exigem um UTXO de colateral dedicado (≥5 ADA). O
  `emissor_sdk` prepara esse colateral automaticamente antes da
  emissão. Se falhar, verifique que a carteira tem saldo suficiente.
- **`PENDING_TRANSACTION` ao emitir via SDK:** a transação anterior
  ainda não confirmou. O `emissor_sdk` aguarda 30s e retenta
  automaticamente. Se persistir entre emissões sequenciais, aumente
  o intervalo entre comandos (`sleep 30` entre cada ator).

Veja também a Seção 5 do guia hands-on (`mao-na-massa.md`).
