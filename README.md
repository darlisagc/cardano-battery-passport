# DPP Workshop Cardano

**De Jequitinhonha a Europa: o Passaporte da Bateria**

Este repositorio implementa um **Passaporte Digital de Produto (DPP)** para baterias de veiculos eletricos, ancorado na **blockchain Cardano** (testnet preprod). O caso de uso rastreia toda a cadeia de suprimentos de uma bateria — desde a **extracao de litio** no Vale do Jequitinhonha (Minas Gerais), passando pela **fabricacao de celulas** em Camacari (Bahia), **montagem do pack** em Sao Bernardo do Campo (Sao Paulo), ate a **reciclagem** em Sorocaba (Sao Paulo). Cada etapa da cadeia e registrada como uma credencial on-chain que referencia a anterior, criando um rastro imutavel e verificavel da materia-prima ate o fim de vida.

Os quatro atores da cadeia de suprimentos sao:

| Ator | Empresa | Funcao |
|------|---------|--------|
| **Ator 1** | MineraLitio Jequitinhonha | Extracao de litio (materia-prima) |
| **Ator 2** | CellTech Brasil | Fabricacao de celulas NMC 811 |
| **Ator 3** | PackMontadora SP | Montagem do pack de bateria 75 kWh |
| **Ator 4** | RecicLar Sorocaba | Reciclagem (fim de vida) |

Cada ator **emite** uma credencial contendo dados do produto (GTIN, origem, pegada de carbono, composicao de materiais) e uma referencia (`ref_*_tx`) apontando para a transacao do ator anterior. O **verificador** percorre essa cadeia de tras para frente — da credencial do pack (ou reciclagem) ate a origem do litio — para reconstruir e validar o passaporte completo.

> **Rede:** tudo roda na **testnet preprod do Cardano** — Blockfrost preprod, faucet de tADA, Cexplorer preprod, API UVerify preprod. Nenhum ADA real e utilizado.

---

## Pre-requisitos

| Componente | Descricao |
|------------|-----------|
| Python | 3.11 ou superior |
| [uv](https://docs.astral.sh/uv/) | Gerenciador de pacotes/venv — instale com `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| IDE | VS Code com extensao Python, PyCharm Community ou similar |
| Carteira Cardano | [Eternl](https://eternl.io) ou [Lace](https://lace.io) configurada em **preprod** |
| tADA | Obtenha ADA de teste no [faucet preprod](https://docs.cardano.org/cardano-testnets/tools/faucet/) |
| Blockfrost | Conta gratuita em [blockfrost.io](https://blockfrost.io) — crie um projeto **preprod** |

## Setup

```bash
uv sync                  # cria .venv e instala todas as dependencias (reproduzivel via uv.lock)
cp .env.example .env     # preencha BLOCKFROST_PROJECT_ID e WALLET_MNEMONIC (SOMENTE TESTNET)
```

`uv sync` e idempotente — rode quantas vezes quiser. Nao precisa ativar o venv manualmente: basta usar `uv run <comando>` de qualquer lugar do projeto e o `uv` cuida do ambiente.

## Emissao

Antes de emitir, certifique-se de ter tADA na carteira preprod cujo mnemonico esta em `WALLET_MNEMONIC`.

Existem **tres formas** de emitir credenciais. Todas produzem credenciais on-chain que o verificador consegue ler:

### Opcao A — Metadata nativa via PyCardano (`emissor_direto`)

Constroi uma transacao Cardano diretamente usando o `TransactionBuilder` do PyCardano, anexando o payload DPP como **metadata nativa da transacao** (label 721). Os dados da credencial sao gravados diretamente na transacao — sem smart contract envolvido.

```bash
uv run python -m verificador_dpp.emissor_direto --ator origem
uv run python -m verificador_dpp.emissor_direto --ator celula
uv run python -m verificador_dpp.emissor_direto --ator pack
uv run python -m verificador_dpp.emissor_direto --ator reciclagem
```

Cada comando imprime o tx hash e atualiza automaticamente o arquivo `.env` (`ATOR1_TX`, `ATOR2_TX`, etc.) para que o proximo ator possa referencia-lo.

### Opcao B — UVerify SDK (`emissor_sdk`)

Emite atraves da plataforma [UVerify](https://uverify.io), que usa **smart contracts Plutus V3** para ancorar a credencial. O SDK cuida da interacao com o smart contract (construcao da transacao Plutus, gerenciamento de state datums, submissao na chain). O modulo de emissao inclui tratamento robusto de erros para o ambiente preprod.

```bash
uv run python -m verificador_dpp.emissor_sdk --ator origem
uv run python -m verificador_dpp.emissor_sdk --ator celula
uv run python -m verificador_dpp.emissor_sdk --ator pack
uv run python -m verificador_dpp.emissor_sdk --ator reciclagem
```

Mesmo comportamento de atualizacao automatica do `.env` da Opcao A.

### Opcao C — Interface web UVerify (sem codigo)

1. Abra <https://app.preprod.uverify.io> e conecte sua carteira preprod.
2. **Issue Certificate** → selecione o template **Digital Product Passport**.
3. Preencha os campos do payload do ator (veja `_payloads.py` como referencia). Para atores 2-4, defina `ref_*_tx` com o tx hash do ator anterior.
4. **Issue** → assine na carteira → copie o tx hash para o `.env` como `ATOR<N>_TX=...`.

### Misturando modos

Voce pode misturar livremente as opcoes A, B e C dentro da mesma cadeia de suprimentos. Por exemplo, emita `origem` via direto (A), `celula` via SDK (B) e `pack` pela interface web (C). O verificador lida com qualquer combinacao.

## Verificacao

```bash
uv run python -m verificador_dpp.verificador              # le TX_HASH_PACK do .env
uv run python -m verificador_dpp.verificador <tx_hash>    # ou passe um tx hash diretamente
```

O verificador percorre a cadeia de credenciais independente de qual opcao de emissao foi usada. A partir da credencial do pack (ou reciclagem), ele segue as referencias `ref_*_tx` de volta pela cadeia — pack → celula → origem — e gera um passaporte consolidado com todos os dados do produto, pegada de carbono e composicao de materiais.

Para verificacao rapida de uma credencial individual via navegador (util para demos ou leitura de QR code):

```
https://app.preprod.uverify.io/verify/<DATA_HASH>
```

Funciona apenas para credenciais emitidas via UVerify (B ou C) e nao reconstroi a cadeia completa.

## Estrutura do projeto

```
cardano-battery-passport/
├── pyproject.toml                          # Configuracao do projeto e dependencias
├── uv.lock                                 # Versoes fixas das dependencias (builds reproduziveis)
├── .env.example                            # Template — copie para .env e preencha suas chaves
├── README.md
├── mao-na-massa.md                         # Guia hands-on passo a passo (pt-BR, workshop de 180 min)
├── arquitetura-dpp.md                      # Detalhamento da arquitetura e decisoes de design
└── src/verificador_dpp/
    ├── __init__.py
    ├── __main__.py                         # Dispatcher de ajuda — mostra comandos disponiveis
    ├── _payloads.py                        # Payloads DPP dos 4 atores (compartilhado por A e B)
    ├── _html_utils.py                      # Helpers HTML: escape e links Cexplorer
    ├── wallet.py                           # Derivacao de carteira HD (CIP-1852) a partir do mnemonico
    ├── emissor_direto.py                   # Opcao A — constroi e submete tx via PyCardano
    ├── emissor_sdk.py                      # Opcao B — emite via UVerify SDK (Plutus V3)
    ├── verificador.py                      # Le e percorre a cadeia de credenciais (cobre A+B+C)
    ├── parser_credencial.py                # Converte metadata do Blockfrost em objetos CredencialDPP
    ├── modelos.py                          # Data classes: CredencialDPP, PassaporteBateria
    ├── relatorio_passaporte.py             # Relatorio texto (saida pt-BR no terminal)
    ├── relatorio_html.py                   # Relatorio HTML — passaporte completo da cadeia
    ├── relatorio_emissao_html.py           # Recibo HTML gerado apos cada emissao
    └── relatorio_reciclagem_html.py        # Relatorio HTML de reciclagem (Ator 4)
```

### O que cada arquivo faz

**Modulos principais:**

- **`_payloads.py`** — Define os dados DPP dos 4 atores. Cada payload e um dicionario de pares chave-valor (nome do produto, GTIN, origem, pegada de carbono, materiais e referencias aos atores anteriores). As opcoes de emissao A e B usam os mesmos payloads, garantindo dados on-chain identicos independente do metodo de emissao.

- **`wallet.py`** — Deriva uma chave de assinatura de pagamento e um endereco preprod a partir de um mnemonico BIP-39 de 24 palavras usando o padrao de derivacao HD CIP-1852. O endereco resultante e o mesmo que voce ve no Eternl ou Lace. Compartilhado por ambos os emissores.

- **`emissor_direto.py`** (Opcao A) — Constroi uma transacao Cardano com o `TransactionBuilder` do PyCardano, anexa o payload DPP como metadata nativa (label 721), assina com a chave da carteira e submete na rede via Blockfrost. Direto e rapido — sem smart contract envolvido.

- **`emissor_sdk.py`** (Opcao B) — Emite atraves do SDK UVerify, que interage com smart contracts Plutus V3 na preprod. Inclui tratamento robusto para limpeza de state datum, preparacao de UTXO de colateral, interpretacao de status codes, assinatura de mensagens CIP-8 e retry com exponential backoff. Veja os comentarios inline no codigo para detalhes de implementacao.

- **`verificador.py`** — O verificador unificado. Dado um tx hash, busca a credencial na chain (tentando primeiro metadata nativa, depois API UVerify), le as referencias `ref_*_tx` e percorre recursivamente a cadeia ate chegar na origem. Funciona com qualquer combinacao de metodos de emissao. Gera um passaporte consolidado no terminal e um relatorio HTML.

**Dados e parsing:**

- **`modelos.py`** — Define `CredencialDPP` (uma credencial individual com dados do produto, materiais e referencias da cadeia) e `PassaporteBateria` (agrupa origem + celula + pack + reciclagem opcional em um passaporte).

- **`parser_credencial.py`** — Converte metadata bruta do Blockfrost (que vem como objetos Namespace aninhados) em objetos `CredencialDPP` estruturados. Trata o formato do template `digitalProductPassport` e classifica campos por prefixo (`ref_*`, `mat_*`, `uv_*`).

**Relatorios:**

- **`relatorio_passaporte.py`** — Gera o relatorio textual do passaporte impresso no terminal apos a verificacao.
- **`relatorio_html.py`** — Gera um relatorio HTML com cards coloridos para cada etapa da cadeia (verde=origem, azul=celulas, amarelo=pack, teal=reciclagem).
- **`relatorio_emissao_html.py`** — Gera um recibo HTML apos cada emissao individual, com link para a transacao no Cexplorer.
- **`relatorio_reciclagem_html.py`** — Gera um relatorio HTML dedicado para a credencial de reciclagem (Ator 4).
- **`_html_utils.py`** — Helpers compartilhados: escape de HTML e geracao de links Cexplorer preprod.

## Dependencias

| Pacote | Finalidade |
|--------|------------|
| `pycardano` (>= 0.11) | Biblioteca Python para Cardano — constroi, assina e submete transacoes |
| `blockfrost-python` (>= 0.6) | Cliente REST da API Blockfrost (acesso a dados da blockchain) |
| `uverify-sdk` (>= 0.1.8) | SDK oficial do UVerify para emissao e verificacao de certificados |
| `python-dotenv` (>= 1.0) | Carrega variaveis de ambiente do `.env` |
| `cbor2 < 6` | Decodificador CBOR (formato de serializacao binaria do Cardano); fixado abaixo de 6 ate suporte do `cbor2pure` |

Versoes exatas estao fixadas no `uv.lock` (commitado para builds reproduziveis).

## Troubleshooting

Para troubleshooting detalhado, mensagens de erro e orientacao passo a passo, veja a **Secao 5** do guia hands-on: [`mao-na-massa.md`](mao-na-massa.md).
