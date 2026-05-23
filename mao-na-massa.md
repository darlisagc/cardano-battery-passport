# Mão na Massa — De Jequitinhonha à Europa

**Workshop:** Passaporte Digital de Produto (DPP) para baterias de veículos elétricos, usando Cardano \+ UVerify \+ Python ([PyCardano](https://github.com/Python-Cardano/pycardano)).

**Duração total do hands-on:** 180 min. 

**Cenário:** quatro atores emitem e verificam credenciais DPP encadeadas que percorrem o ciclo de vida completo de uma bateria brasileira.

---

## ⚠️ Nota sobre rede

 O workshop inteiro — carteira, faucet, Cexplorer, Blockfrost, UVerify — usa **preprod**.   
---

## A história — De Jequitinhonha à Europa

A partir de **fevereiro de 2027**, a União Europeia passa a exigir um **Battery Passport** digital para todo pack EV que entrar na Europa. Sem passaporte, sem mercado europeu. O Brasil tem os ingredientes — lítio no Vale do Jequitinhonha (MG), fábricas em Camaçari (BA) e em São Bernardo do Campo (SP), regulação de logística reversa (PNRS) — mas falta a camada técnica que prove, para qualquer parte, **de onde aquele pack veio e o que aconteceu com ele**.

Neste hands-on, **você interpreta os quatro atores** de uma única cadeia:

- Em **2026**, a *MineraLitio* extrai um lote de Li₂CO₃ em Araçuaí (MG) e emite o primeiro DPP — **origem**.   
- Logo depois, a *CellTech* monta células NMC em Camaçari (BA) e emite **célula**, referenciando *origem*.   
- Em São Bernardo do Campo (SP), a *PackMontadora* monta o pack de 75 kWh e emite **pack**, referenciando *célula*.   
- Em **2028** o pack viaja num EV brasileiro exportado para a UE; depois da vida útil em algum estacionamento de Brussels, **dez anos depois** o pack volta ao Brasil e cai na *RecicLar*, em Sorocaba (SP), que **verifica a cadeia inteira on-chain antes de processar** — só então emite o DPP de **reciclagem**, fechando o ciclo.

Cada DPP é uma transação no Cardano. As **referências cruzadas** entre as credenciais (`cert_*_credential_tx`) são o que torna a cadeia auditável por *qualquer parte* — regulador europeu, comprador europeu, recicladora brasileira — sem pedir permissão a um gatekeeper.

---

### Fluxo do hands-on

Cada fase abaixo corresponde a uma seção deste documento. Siga em ordem.

#### 1️⃣ SETUP — Seção 0

**Pré-requisitos:** Python 3.11+, [uv](https://docs.astral.sh/uv/) instalado, carteira Cardano em preprod (Eternl/Lace), tADA do faucet, projeto Blockfrost preprod, starter clonado e `uv sync` rodado.

                 ⬇

#### 2️⃣ TEORIA — Seção 1

Entender o template `digitalProductPassport` do UVerify e a convenção do workshop de encadear credenciais via `cert_*_credential_tx`.

                ⬇

#### 3️⃣ EMISSÃO — Seção 2

Quatro atores em sequência, cada um depende do anterior:

| \# | Ator | Comando | Saída | Depende de |
| :---- | :---- | :---- | :---- | :---- |
| 1 | origem | `--ator origem` | `ATOR1_TX` | — |
| 2 | célula | `--ator celula` | `ATOR2_TX` | `ATOR1_TX` |
| 3 | pack | `--ator pack` | `ATOR3_TX` · `TX_HASH_PACK` · `DATA_HASH_PACK` | `ATOR2_TX` |
| 4 | reciclagem | `--ator reciclagem` | `ATOR4_TX` | `ATOR1`, `ATOR2`, `ATOR3` |

Cada ator pode ser emitido por **três caminhos**:

- **Opção A** — `emissor_direto.py` (PyCardano `TransactionBuilder`, sem UVerify)  
- **Opção B** — `emissor_sdk.py` (`uverify-sdk`, Python)  
- **Opção C** — UI UVerify (sem código, em [https://app.preprod.uverify.io](https://app.preprod.uverify.io))

                        ⬇

#### 4️⃣ VERIFICAÇÃO — Seção 3

Pega `TX_HASH_PACK` e segue a cadeia até a origem com **`verificador.py`** (verifica qualquer combinação  A+B+C). 

                     ⬇

#### 5️⃣ FECHAMENTO

- **Seção 4** — Recicladora valida antes de processar  
- **Seção 5** — Troubleshooting

### Os 4 atores da cadeia (detalhe da Seção 2\)

| \# | Ator | Empresa (fictícia) | Local |
| :---- | :---- | :---- | :---- |
| ① | origem | MineraLitio | Vale do Jequitinhonha, MG |
| ② | célula | CellTech | Camaçari, BA |
| ③ | pack | PackMontadora | São Bernardo do Campo, SP |
| ④ | reciclagem | RecicLar | Sorocaba, SP |

A ④ reciclagem referencia **todas** as anteriores — após reciclar, o pack deixa de existir e a credencial de reciclagem se torna o ponteiro definitivo da cadeia.

### Opções A, B e C

|  | A — Python | B — Python via UVerify SDK | C — UI UVerify |
| :---- | :---- | :---- | :---- |
| **Emissão** | `emissor_direto.py` — você monta a tx com PyCardano | `emissor_sdk.py` — o SDK monta contra a API do UVerify  | [https://app.preprod.uverify.io](https://app.preprod.uverify.io) (sem código) |
| **Verificação** | unificada — qualquer combinacao A+B+C usa `verificador.py` (Seção 3\) | mesmo | mesmo -  para verificar a transacao feita pelo UVerify UI `https://app.preprod.uverify.io/verify/<data_hash>` |
| **O que ensina** | Tx-building e leitura de metadata bruta | Atalho via SDK \- abstrai a complexidade | UX final do UVerify (o que o usuário vê) |
| **Dependências** | `pycardano` \+ `blockfrost-python` | `uverify-sdk` (+ PyCardano só para assinar) | Apenas browser \+ carteira preprod |
| **Quando usar** | Auditoria independente, regulador, integração customizada | Use seu stack atual; o UVerify ancora a prova de integridade no Cardano | Praticidade, demo, primeiro contato, validação manual |

💡 **Recomendação:** caminho misto sugerido — atores 1 e 2 pela **Opção A** (`emissor_direto`), ator 3 pela **Opção B** (`emissor_sdk`), ator 4 pela **Opção C** (UI). Para verificar a cadeia toda, use o `verificador` (Seção 3.5)  

Estado do .env ao longo do workshop

Cada emissão imprime um `tx_hash` e um `data_hash` (ambos os emissores Python) que é adicionado ao `.env` conforme avança:

| Após rodar | Variáveis `.env` |
| :---- | :---- |
| `--ator origem` | `ATOR1_TX` |
| `--ator celula` | `ATOR2_TX` |
| `--ator pack` | `ATOR3_TX` · `TX_HASH_PACK` · `DATA_HASH_PACK` |
| `--ator reciclagem` | `ATOR4_TX` |

💡 **Por que repetir** `TX_HASH_PACK` **para o**  `ATOR3_TX`**?**   
Porque o verificador da Seção 3 lê `TX_HASH_PACK` (entrada da cadeia da bateria), enquanto o emissor da reciclagem lê `ATOR3_TX` (referência cruzada `cert_pack_credential_tx`). São o mesmo hash, em duas variáveis.

### Atalho — qual comando rodar quando

```shell
# SETUP (uma vez) — idempotente, so instala o que falta
uv sync
cp .env.example .env
# preencha BLOCKFROST_PROJECT_ID e WALLET_MNEMONIC no .env

# EMISSÃO — cada emissor atualiza o .env automaticamente
uv run python -m verificador_dpp.emissor_direto --ator origem
uv run python -m verificador_dpp.emissor_direto --ator celula
uv run python -m verificador_dpp.emissor_direto --ator pack
uv run python -m verificador_dpp.emissor_direto --ator reciclagem

# (mesmo padrao com emissor_sdk se quiser ver a Opção B —
#  ou misture: 1+2 via direto, 3 via sdk, 4 via UI; recomendado)

# VERIFICAÇÃO — único verificador, valida qualquer combinacao A+B+C
uv run python -m verificador_dpp.verificador
```

##  

## 

## Seção 0 — Pré-requisitos

### 0.1 Ambiente local

| Componente | Versão | Link |
| :---- | :---- | :---- |
| Python | 3.11+ | [https://www.python.org/downloads/](https://www.python.org/downloads/) |
| uv | 0.5+ | [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/) |
| IDE | VS Code com Python extension |  |
| Git | qualquer versão recente |  |

Instalar `uv` (gerenciador de pacotes/venv que substitui o `pip`):

```shell
curl -LsSf https://astral.sh/uv/install.sh | sh   # macOS / Linux
# Windows (PowerShell): irm https://astral.sh/uv/install.ps1 | iex
```

Verifique:

```shell
uv run python --version  # Python 3.11.* ou superior
uv --version        # uv 0.5.* ou superior
```

### 0.2 Carteira Cardano em preprod

1. Instale [Eternl](https://eternl.io) (browser extension) ou [Lace](https://lace.io).  
2. Crie uma **nova carteira** (não use mainnet para o workshop).  
3. Troque a rede para **preprod** (Eternl: Settings → Network → Preprod).  
4. Anote o **endereço de pagamento** (começa com `addr_test1...`).  
   

### 0.3 tADA do faucet

1. Acesse [https://docs.cardano.org/cardano-testnets/tools/faucet/](https://docs.cardano.org/cardano-testnets/tools/faucet/)  
2. Selecione **Preprod Testnet**, cole o endereço da carteira, receba **10.000 tADA**.  
3. Confirme a chegada dos fundos na carteira (pode levar 1--2 min).

### 0.4 UVerify

1. Abra [https://app.preprod.uverify.io/](https://app.preprod.uverify.io/) .  
2. Click na opção “Create”  
3. Conecte a carteira preprod (botão *Connect Wallet*).  
4. Selecione a sua carteira digital / Wallet recém criada   
   

### 0.5 Blockfrost (somente para a Seção 3 — verificador Python)

1. Crie conta gratuita no [https://blockfrost.io](https://blockfrost.io).  
2. Click “Dashboard”  
3. Caso você já tenha criado uma conta, faça o login com seu e-mail. Do contrário, você pode fazer o sign in com a sua conta de email, github ou gitlab.   
4. *Add project* → **Cardano preprod** → nomeie como `workshop-dpp` \-\> Save   
5. Copie o **Project ID** (começa com `preprod...`). Guarde — você vai colar no `.env` mais tarde.

### 0.6 Starter repo

```shell
git clone https://github.com/darlisagc/cardano-dpp-workshop
cd cardano-dpp-workshop
uv sync                  # cria .venv, lê pyproject.toml, instala tudo do uv.lock
cp .env.example .env     # vamos preencher na proxima secao
```

O `uv sync` é **idempotente**: pode rodar quantas vezes quiser — só instala o que falta. Confere automaticamente que você tem Python 3.11+ e cria o `.venv` para você.

Você **não precisa** ativar o virtualenv. Use `uv run <comando>` em qualquer subdiretório do projeto e o uv resolve o ambiente:

```shell
uv run python -m verificador_dpp.emissor_direto --ator origem
```

(Se preferir o fluxo clássico, `source .venv/bin/activate` continua funcionando.)

## Seção 1 — Entendendo o template DPP do UVerify

### 1.1 Abrindo o template

1. Va a  [https://app.preprod.uverify.io/](https://app.preprod.uverify.io/) .  
2. Click na opção “Create”  
3. Apos isto, selecione “Write Text” e digite "DPP certificado bateria".  
4. Escolha o template **Digital Product Passport**.  
5. Observe os campos — vamos mapear cada um para um estágio do ciclo de vida da bateria.

### 1.2 Mapa dos campos

UVerify DDP template: [https://docs.uverify.io/templates/built-in](https://docs.uverify.io/templates/built-in)

| Campo UVerify | Tipo | Papel na bateria |
| :---- | :---- | :---- |
| `uverify_template_id` | obrigatório (fixo) | sempre `digitalProductPassport` |
| `name` | obrigatório | nome do produto/lote (ex: "Lote Lítio Jequitinhonha 2026-03") |
| `issuer` | obrigatório | razão social do ator emissor |
| `gtin` | obrigatório | identificador global (GS1). No workshop usamos GTIN-13 fictícios |
| `uv_url_serial` | obrigatório | **sha256(serial)** — o serial em si fica off-chain |
| `origin` | opcional | "Jequitinhonha, MG, BR" etc. |
| `manufactured` | opcional, ISO 8601 | data do lote |
| `carbon_footprint` | opcional | ex: "4.2 kg CO₂e/kg Li₂CO₃" |
| `recycled_content` | opcional | ex: "0%" na origem, "12%" no pack |
| `mat_*` | mapa opcional | composição (ex: `mat_litio: 98%`) |
| `cert_*` | mapa opcional | certificações. **Também usamos aqui para encadear credenciais** — ver 1.4 |

### 

### 1.3 Ancoragem on-chain

O UVerify calcula `hash = sha256(gtin + serialNumber)` localmente e constrói uma transação Cardano que:

1. **Interage com o smart contract Plutus do UVerify** — gasta um UTxO no endereço de script da plataforma e cria um novo UTxO no mesmo endereço, mantendo o "fio" de anchoring sob controle do validador.  
2. **Anexa o hash \+ os campos do template como metadados da transação** (via `tx_metadata`).  
3. **Pede sua carteira para assinar** e transmite na rede preprod.

O serial completo nunca sai do seu navegador — só o hash entra na blockchain. O produto é verificado via URL do tipo `https://app.preprod.uverify.io/verify/<data_hash>/<index>?serial=<serial>`.

### 1.4 Encadeamento

O template não tem um campo "credencial anterior" nativo. Usamos o mapa `cert_*` para referenciar transações anteriores, seguindo a convenção:

```
cert_origem_credential_tx  → tx hash da credencial de origem (Ator 1)
cert_celula_credential_tx  → tx hash da credencial de célula (Ator 2)
cert_pack_credential_tx    → tx hash da credencial de pack (Ator 3)
```

Além do tx hash, cada referência inclui um **hint de `data_hash`** — necessário para que o verificador consiga buscar credenciais emitidas via UVerify (Opções B/C) na API:

```
cert_origem_data_hash      → sha256(gtin + serial) do Ator 1
cert_celula_data_hash      → sha256(gtin + serial) do Ator 2
cert_pack_data_hash        → sha256(gtin + serial) do Ator 3
```

O verificador Python da Seção 3 segue esses ponteiros (`cert_*_credential_tx` + `cert_*_data_hash`) para reconstruir a cadeia completa.

### 1.5 Emissão vs verificação

| Operação | Quem faz | O que acontece |
| :---- | :---- | :---- |
| Emissão (**write**) | Ator com carteira | Assina e submete tx com metadados (Seção 2 — Opção A, B ou C) |
| Verificação (**read**) | Qualquer pessoa | Lê on-chain — sem chave (Seção 3 — `verificador`) |

É por isso que **só os emissores precisam de carteira**; os verificadores são read-only e podem ser rodados por qualquer parte (regulador, consumidor, recicladora) sem credenciais.

### 1.6 Dois padrões de ancoragem on-chain

Existem **duas formas distintas** de ancorar um DPP em Cardano, que definem **onde o payload realmente vive** e como qualquer parte o lê. As Opções A vs B/C deste workshop instanciam exatamente esses dois padrões:

| Padrão | Onde fica o payload | Como ler | Opções no workshop |
| :---- | :---- | :---- | :---- |
| **Metadata nativa Cardano** | Direto na transação, em `auxiliary_data` sob um label numérico (`1990` neste workshop) | Qualquer indexador Cardano: Blockfrost, Yaci Store, db-sync | **Opção A** (`emissor_direto`) |
| **Anchor \+ off-chain** | Só um hash (`sha256(gtin+serial)`) gravado em datum de um output de script; payload rico vive no banco da UVerify | API REST da UVerify: `verify_by_transaction(tx, hash)` | **Opções B e C** (SDK e UI) |

**Trade-offs:**

|  | Metadata nativa | Anchor \+ off-chain (UVerify) |
| :---- | :---- | :---- |
| Custo de tx | Maior — paga por byte de metadata | Menor — só o hash \+ envelope on-chain |
| Privacidade | Tudo público on-chain | Só o hash on-chain; payload pode ter ACL no servidor |
| Dependência externa | Nenhuma — qualquer indexador Cardano | UVerify precisa estar no ar para resolver o payload |
| Auditabilidade | Total, sem terceiros | Tamper-evidence garantida pelo hash; conteúdo depende do UVerify |
| [Padrão Cardano Foundation DPP Standards](https://github.com/cardano-foundation/cardano-dpp-standards) | *Event Log* | *Static Passport Anchor* |

**Quando usar cada um:**

- **Metadata nativa** — payloads pequenos, dados que precisam ser lidos por **qualquer parte sem dependência** (auditoria pública, regulador, integração customizadas, etc).  
- **Anchor \+ off-chain** — payloads grandes, dados parcialmente sensíveis (ACL), ou quando você quer **UX pronta** (formulário, página de verificação, QR code).

Os dois padrões **coexistem na mesma cadeia** — neste workshop, atores 1+2 usam metadata nativa, atores 3+4 usam anchor UVerify, e o `verificador` faz fallback automático entre os dois para reconstruir o passaporte completo.

## 

## Seção 2 — Emitindo credenciais via Python

Esta seção mostra **três formas** de emitir credenciais DPP em Cardano preprod:

| Opção | Como funciona | Dependência principal |
| :---- | :---- | :---- |
| **A — Python direto** | Você constrói a transação do zero com `TransactionBuilder` e anexa o payload DPP como metadata nativa | PyCardano \+ Blockfrost |
| **B — Python via SDK** | O SDK do UVerify monta a transação contra a API do mesmo; seu código só assina | `uverify-sdk` |
| **C — UI UVerify** | Browser \+ carteira; sem código — você preenche o formulário em `app.preprod.uverify.io` | apenas browser |

💡 **Recomendação:** caminho misto sugerido — ators 1 e 2 pela **Opção A**, ator 3 e 4 pela **Opção B**, ou ator 4 pela **Opção C** (UI). Verifique a cadeia toda com `verificador` (Seção 3.5).

### 2.1 Configuração antes de emitir

Edite `.env`:

```
BLOCKFROST_PROJECT_ID=preprod<seu_project_id>
WALLET_MNEMONIC=palavra1 palavra2 ... palavra24    # Preprod ONLY
```

⚠️ **Preprod ONLY.** Cole apenas o mnemônico de uma carteira **preprod** que já recebeu tADA do faucet (Seção 0.3). **Nunca** cole um mnemônico mainnet em arquivo de texto.

A derivação segue CIP-1852 (`m/1852'/1815'/0'/0/0` para pagamento, `m/1852'/1815'/0'/2/0` para stake), o mesmo que Eternl/Lace usam: o endereço derivado pelo Python coincide com o endereço da sua carteira. tADA do faucet vale para os dois.

### 2.2 Payload DPP — compartilhado pelas duas opções

Os payloads dos quatro atores ficam em `_payloads.py`, seguindo o template `digitalProductPassport` ([https://docs.uverify.io/templates/built-in](https://docs.uverify.io/templates/built-in)):

| Campo | Obrigatório | Comentário |
| :---- | :---- | :---- |
| `uverify_template_id` | sim | Sempre `"digitalProductPassport"` |
| `name`, `issuer`, `gtin` | sim | identidade do lote |
| `uv_url_serial` | sim | `sha256(serial)` — diferente do `hash` |
| `cert_*_credential_tx` | convenção do workshop | refs encadeadas (tx hash do ator anterior) |
| `cert_*_data_hash` | convenção do workshop | sha256(gtin+serial) do ator referenciado — hint para lookup UVerify |
| `mat_*` | opcional | composição |
| `cert_*` | opcional | certificações |
| `origin`, `manufactured`, `carbon_footprint`, … | opcional | demais campos do template |

⚠️ Todos os valores são **strings** — exigência do `CertificateData.metadata: Dict[str, str]` e do limite de 64 bytes por string da metadata Cardano (transaction size 16KB).

**Encadeamento.** Cada payload aponta para os atores anteriores via dois campos por referência — o **tx hash** (para localizar a transação) e o **data_hash** (hint para lookup UVerify):

```
celula       cert_origem_credential_tx  → ATOR1_TX
             cert_origem_data_hash      → sha256(gtin + serial) do Ator 1

pack         cert_celula_credential_tx  → ATOR2_TX
             cert_celula_data_hash      → sha256(gtin + serial) do Ator 2

reciclagem   cert_pack_credential_tx    → ATOR3_TX
             cert_pack_data_hash        → sha256(gtin + serial) do Ator 3
             cert_celula_credential_tx  → ATOR2_TX
             cert_celula_data_hash      → sha256(gtin + serial) do Ator 2
             cert_origem_credential_tx  → ATOR1_TX
             cert_origem_data_hash      → sha256(gtin + serial) do Ator 1
```

É essa cadeia que o verificador da Seção 3 vai seguir. Os campos `cert_*_data_hash` são essenciais para cadeias mistas — sem eles, o verificador não consegue localizar credenciais emitidas via UVerify (Opções B/C) na API.

### 2.3 Opção A — Emissor direto (PyCardano)

Esta opção é **puramente Python & Cardano** — usa apenas PyCardano para montar a transação, anexa o payload DPP como **metadata nativa**, e submete via Blockfrost. **Nenhuma chamada à infra do UVerify** acontece (nem na emissão, nem depois). Implementa o padrão *Event Log* (ver 1.6).

O script em `emissor_direto.py`:

1. Monta o payload DPP em memória (`_payloads.py`, schema documentado em 1.2).  
2. Conecta ao Blockfrost preprod via `BlockFrostChainContext`.  
3. Constrói uma tx com `TransactionBuilder` e anexa o payload como `AuxiliaryData(Metadata({1990: payload}))`. Como toda tx Cardano precisa de pelo menos um output (UTxO model) e não estamos pagando ninguém, deixamos o `change_address` mandar o leftover (`input - fee`) **de volta para o nosso próprio endereço** — vira um novo UTxO seu. **O custo real é apenas o fee da rede (\~0.18 tADA)**.  
4. Assina com a chave HD derivada do mnemônico.  
5. Submete via Blockfrost e devolve o tx hash.

**Trecho-chave**

```py
from pycardano import (
    AuxiliaryData, BlockFrostChainContext, Metadata, TransactionBuilder,
)
from blockfrost import ApiUrls

# Passo 3 — conectar ao Blockfrost preprod
context = BlockFrostChainContext(
    project_id=project_id, base_url=ApiUrls.preprod.value
)

# Passo 4 — montar a tx
#   - input:  UTxOs encontrados no nosso endereco
#   - output: nenhum explicito — change_address (Passo 5) manda o leftover
#             (input - fee) de volta para o nosso proprio endereco
#   - aux:    payload DPP como metadata Cardano (label 1990)
builder = TransactionBuilder(context)
builder.add_input_address(address)
builder.auxiliary_data = AuxiliaryData(Metadata({1990: payload}))

# Passo 5 — build_and_sign calcula fee, escolhe UTxOs, monta o output
# de change para `change_address`, e assina com a chave passada
signed_tx = builder.build_and_sign(
    signing_keys=[payment_skey], change_address=address
)

# Passo 6 — submeter; em ~20-40s aparece em Cexplorer
context.submit_tx(signed_tx)
```

**Rodar (em ordem):**

```shell
uv run python -m verificador_dpp.emissor_direto --ator origem
uv run python -m verificador_dpp.emissor_direto --ator celula
```

**`Eg :tx --ator origem`**  
[**`https://preprod.cexplorer.io/tx/722de44575ad8936bbd65685f9d2c3c2a12d6cd58887828dda8b2ea55a589df1?tab=metadata`](https://preprod.cexplorer.io/tx/722de44575ad8936bbd65685f9d2c3c2a12d6cd58887828dda8b2ea55a589df1?tab=metadata)**

**`Eg :tx --ator  celula`**  
[**`https://preprod.cexplorer.io/tx/61c943e5a80e57b182a1774d2b6f44045327bd61253b1ead530bb256af1a409e?tab=metadata`](https://preprod.cexplorer.io/tx/61c943e5a80e57b182a1774d2b6f44045327bd61253b1ead530bb256af1a409e?tab=metadata)**

💡 **`.env` atualizado automaticamente.** Após cada emissão, o script grava o `tx_hash` e `data_hash` direto no `.env` — você não precisa copiar/colar entre os comandos. A última linha do output mostra exatamente quais chaves foram escritas (`ATOR1_TX=…`, `TX_HASH_PACK=…`, etc.).

💡 **Label de metadata.** Usamos `1990` (escolha arbitrária, homenagem à Lei do Consumidor brasileira). Cardano metadata aceita qualquer inteiro \>= 1; o `verificador` escaneia **todos** os labels procurando o campo `uverify_template_id` (nossa convenção de schema — ver 1.6), então o número escolhido não afeta a verificação. Você poderia trocar o schema por outro DPP — desde que o verificador conheça o novo formato.

### 2.4 Opção B — Emissor via UVerify SDK

Com `uverify-sdk`. O SDK monta a transação contra a API REST do UVerify; seu código só provê uma callback de assinatura, que internamente delega ao PyCardano.

**Fluxo:**

```
[seu codigo]                  [UVerify API]               [Cardano preprod]
     |                              |                              |
     |--- POST /transaction/build ->|                              |
     |<-- unsigned_tx (CBOR-hex) ---|                              |
     |                              |                              |
   sign_tx callback (PyCardano)     |                              |
     |                              |                              |
     |-- POST /transaction/submit ->|--- submit assinada --------->|
     |<--- tx_hash -----------------|                              |
```

**Anatomia da callback** (`emissor_sdk.py`):

```py
from pycardano import (
    Transaction, TransactionWitnessSet, VerificationKeyWitness,
)

def sign_tx(unsigned_cbor_hex: str) -> str:
    # Passo 1 — decodifica a tx que veio do UVerify (CBOR-hex string)
    tx = Transaction.from_cbor(unsigned_cbor_hex)

    # Passo 2 — hash do body (o que o Cardano espera ver assinado)
    body_hash = tx.transaction_body.hash()

    # Passo 3 — assinatura Ed25519 sobre o body_hash (64 bytes)
    signature = payment_skey.sign(body_hash)

    # Passo 4 — Cardano espera vkey Ed25519 normal de 32 bytes
    # (sem o chain code de 32 bytes do CIP-1852 estendido)
    vkey = payment_skey.to_verification_key().to_non_extended()
    witness = VerificationKeyWitness(vkey, signature)

    # Devolve o witness set em CBOR-hex - formato que o SDK espera
    return TransactionWitnessSet(vkey_witnesses=[witness]).to_cbor_hex()
```

Pontos críticos:

- `to_non_extended()` é essencial: a witness Cardano usa a chave pública Ed25519 de **32 bytes** — sem o chain code do CIP-1852.  
- A assinatura é dos **64 bytes** do hash do `transaction_body`.

**Emissão** (uma chamada):

```py
from uverify_sdk import UVerifyClient
from uverify_sdk.models import CertificateData

# Passo 3 — embrulha tudo num CertificateData:
#   - hash:      sha256(gtin + serial) - id do produto
#   - algorithm: SHA-256
#   - metadata:  o payload DPP (template digitalProductPassport)
cert = CertificateData(
    hash=sha256((gtin + serial).encode()).hexdigest(),
    algorithm="SHA-256",
    metadata=payload,
)

# Passo 4 — cliente UVerify (default base_url = api.preprod.uverify.io)
# O SDK por baixo:
#   1. POSTa /api/v1/transaction/build  -> recebe tx CBOR-hex
#   2. chama nossa sign_tx callback     -> recebe witness CBOR-hex
#   3. POSTa /api/v1/transaction/submit -> recebe tx_hash
client = UVerifyClient()
tx_hash = client.issue_certificates(
    address=str(address),
    certificates=[cert],
    sign_tx=sign_tx,
)
```

**Rodar:**

```shell
uv run python -m verificador_dpp.emissor_sdk --ator pack
uv run python -m verificador_dpp.emissor_sdk --ator reciclagem
```

**`Eg :tx --ator pack`**  
[**`https://preprod.cexplorer.io/tx/4158020f913cb7c8aa8ca35648d9af34f54822b1fb8655c05af2f20ab38081ee?tab=content`](https://preprod.cexplorer.io/tx/4158020f913cb7c8aa8ca35648d9af34f54822b1fb8655c05af2f20ab38081ee?tab=content)** 

**`Eg :tx --ator reciclagem`**  
[**`https://preprod.cexplorer.io/tx/25b44923d8f4be16e3aa9aa733e54a155f59a9132b0d35514b24b564560d7166`](https://preprod.cexplorer.io/tx/25b44923d8f4be16e3aa9aa733e54a155f59a9132b0d35514b24b564560d7166)** 

💡 **`.env` atualizado automaticamente** — igual ao `emissor_direto`. Cada emissão grava `ATOR<N>_TX` e `DATA_HASH` no `.env`; quando o ator é `pack`, também grava `TX_HASH_PACK`  (este último é usado pelo `verificador` como hint inicial quando o pack veio de B/C).

### 2.5 Opção C — Emissão via UI UVerify (sem código)

Não escreve uma linha de Python. Use o app oficial do UVerify em [https://app.preprod.uverify.io](https://app.preprod.uverify.io). Útil para sentir o produto, fazer demos, ou validar manualmente o que os scripts estão emitindo.

**Passo a passo:**

1. **Conectar carteira.** Acesse [https://app.preprod.uverify.io](https://app.preprod.uverify.io) → *Create* → Selecione Digital Product Passaport no “Certificate Template” . Connect Wallet → escolha **Eternl** ou **Lace** → garanta que a rede está em **preprod**   
     
2. **Iniciar emissão.** Selecione “Write Test”→ Digite DPP →  *Issue Certificate* → escolha o template **Digital Product Passport**.  
     
3. **Preencher o formulário.** Cole os campos do payload do ator desejado (use os valores em `_payloads.py` como referência — ou copie do JSON na Seção 2.2).   
     
4. **Criar Certificado.** Clique em **Create Trust Certificate** → a carteira (Eternl/Lace) abre um popup de assinatura → Digite sua senha e **Sign**. Aguarde \~20-40 s pela confirmação on-chain.

**`Eg: UVerify UI Validator`**  
**`https://app.preprod.uverify.io/verify/4c075ab0d85a1e3ee249ccac594d188eb23c8d0d4b8aa890e795e92f550f45fb/2?serial=ML-JQT-2026-03-043`**

5. **Copiar o tx hash.** A tela de sucesso mostra o tx hash da emissão. Copie-o e cole no `.env`:

💡 **Encadeamento manual.** Diferente das Opções A e B (onde o `_payloads.py` já injeta as referências cruzadas), na UI você precisa colar os tx hashes anteriores nos campos `cert_*` *à mão*. Isso reforça a noção de que o encadeamento é **convenção**, não mágica.

## Seção 3 — Verificando credenciais via Python

Diferente da emissão (três opções A/B/C), a **verificação é unificada**: um módulo, `verificador.py`, valida qualquer cadeia DPP independente de qual opção emitiu cada credencial. O motivo é simples:

- Credenciais emitidas via `emissor_direto` (Opção A) gravam o payload completo na **metadata nativa** do Cardano — qualquer indexador Cardano lê.  
- Credenciais emitidas via UVerify (Opções B/C) gravam só um *anchor hash* em **script datum**; o payload rico fica off-chain, indexado pela API do UVerify por `data_hash`.

Os dois caminhos vivem na mesma cadeia, e qualquer cadeia real do workshop (recomendação: 1+2 via A, 3 via B, 4 via C) é heterogênea. O `verificador` faz fallback automático entre os dois.

### 3.1 Pré-requisitos no `.env`

```
BLOCKFROST_PROJECT_ID=preprod<seu_project_id>
TX_HASH_PACK=<ATOR3_TX>
DATA_HASH_PACK=<data_hash do pack>     # necessário se o pack foi emitido via UVerify (B/C)
```

`TX_HASH_PACK` é a entrada da cadeia. `DATA_HASH_PACK` é usado como **hint inicial** para o pack quando ele veio do UVerify (a API do UVerify pede pelo hash do documento). Para os atores 2 e 1 da cadeia, o `data_hash` é propagado automaticamente via os campos `cert_*_data_hash` de cada credencial, e também pode ser extraído dos redeemers on-chain.

### 3.2 verificador.py — fluxo completo

`verificador.py` é o único verificador do workshop. Para cada transação da cadeia, ele tenta dois caminhos em ordem:

**Caminho 1 — Metadata nativa Cardano** (Blockfrost). Se a tx foi emitida pelo `emissor_direto`, o payload DPP completo está aqui — basta parsear (`parser_credencial.py`) e converter para `CredencialDPP`.

**Caminho 2 — API do UVerify** (fallback). Se o passo 1 não achou `uverify_template_id`, a tx é provavelmente uma emissão UVerify (SDK ou UI), que guarda só um *anchor hash* em script datum, com o payload off-chain. O verificador então reúne candidatos a `data_hash` de **três fontes** (em ordem de prioridade):

1. **Hint da cadeia** — campo `cert_*_data_hash` propagado pela credencial que referencia esta tx. É o mais prático: cada credencial já carrega o `sha256(gtin+serial)` do ator que referencia.
2. **Redeemer on-chain** — o verificador lê o redeemer da transação via Blockfrost e extrai o hash do `UVerifyCertificate` (caminho: `redeemer.fields[1].list[*].fields[0].bytes`). Funciona para todas as opções (A/B/C), inclusive credenciais emitidas via UI.
3. **Inline datum** — fallback heurístico: extrai todas as sequências de 32 bytes do inline datum. Menos confiável porque o datum contém outros hashes (como `certificate_data_hash` e `id`) que não são o `data_hash` do produto.

Para cada candidato, o verificador faz um **HTTP GET direto** na API pública do UVerify (`/api/v1/verify/by-transaction-hash/{tx}/{dh}`) em vez de usar o SDK Python — isso evita um `RecursionError` causado pela resposta JSON profundamente aninhada (o campo `stateDatum` pode ter centenas de níveis de histórico). O verificador extrai apenas o campo `extra` (onde está a metadata) via regex, sem parsear o JSON inteiro.

Após resolver cada credencial (por qualquer caminho), o verificador segue `cert_*_credential_tx` + `cert_*_data_hash` references para o próximo nó. Repete por 3 atores: **pack → célula → origem**.

**Trecho-chave** (`verificador.py`):

```py
def buscar_credencial(blockfrost, uverify, parser, tx_hash, data_hash_hint=None):
    # Caminho 1 — metadata nativa Cardano
    metadata = blockfrost.transaction_metadata(tx_hash)
    if metadata:
        try:
            return parser.extrair_credencial(metadata)
        except Exception:
            pass  # cai no fallback UVerify

    # Caminho 2 — UVerify API com candidatos a data_hash de 3 fontes:
    #   1. hint da credencial anterior (cert_*_data_hash)
    #   2. redeemer on-chain (hash real do certificado)
    #   3. inline datum (heurístico — sequências de 32 bytes)
    candidatos = [data_hash_hint] if data_hash_hint else []
    candidatos += extrair_candidatos_data_hash(blockfrost, tx_hash)
    for dh in candidatos:
        try:
            # HTTP direto (evita RecursionError do SDK)
            return verify_by_transaction_direct(tx_hash, dh)
        except (UVerifyApiError, HTTPError):
            continue
    raise RuntimeError("nao consegui localizar a credencial")
```

**Rodar:**

```shell
uv run python -m verificador_dpp.verificador
# ou:
uv run python -m verificador_dpp.verificador <tx_hash_pack>
```

**Saída esperada** (cadeia mista 1+2 via A, 3 via B, 4 via C):

```
================================================================
Verificador DPP - Workshop Cardano
De Jequitinhonha a Europa: o Passaporte da Bateria
================================================================

[1/4] Buscando credencial do pack...
      OK - Pack EV 75kWh - SP-2026-04-155
[2/4] Seguindo referencias para as celulas...
      OK - Celulas NMC 811 - Lote BA-2026-04-008
[3/4] Seguindo referencias para a origem do litio...
      OK - Lote Litio Jequitinhonha 2026-03
[4/4] Montando relatorio do passaporte...

================================================================
  PASSAPORTE VALIDO
================================================================

-- Origem (lítio) --
  Emitente: MineraLitio Jequitinhonha Ltda.
  Produto: Lote Litio Jequitinhonha 2026-03
  ...
```

🎯 **Insight:** o relatório final não distingue qual ator foi emitido por qual canal. Esse é o ponto — **a cadeia on-chain é a única fonte de verdade**, independente de como cada credencial chegou lá.

### 3.3 Atalho — verificação ad-hoc via URL UVerify (sem código)

Para inspecionar **uma** credencial individual sem rodar código (útil para demos ou para o consumidor final que escaneia um QR code):

```
https://app.preprod.uverify.io/verify/<DATA_HASH>
https://app.preprod.uverify.io/verify/<DATA_HASH>?serial=<SERIAL>
```

A página exibe os campos do template DPP em formato legível, o tx hash, o emissor e a data de criação. O `data_hash` aparece como **Unique Product Identifier** na página da credencial.

⚠️ **Limitações:** funciona apenas em credenciais emitidas via UVerify (Opções B ou C) — credenciais do `emissor_direto` (Opção A) não estão indexadas pelo UVerify. E não monta a cadeia — para reconstruir origem→célula→pack, use o `verificador`.

## Seção 4 — Fechando o ciclo: a recicladora

### 4.1 Verificação antes de reciclar

O Ator 4 (RecicLar, Sorocaba/SP) **não confia** em palavra — roda um dos verificadores da Seção 3 contra o hash do pack que recebeu. Se o relatório der "***PASSAPORTE VALIDO***" e a cadeia bater, a recicladora tem garantia de procedência ambiental e ESG.

### 4.2 Emissão da credencial de reciclagem

A credencial do Ator 4 já foi emitida na Seção 2 quando você rodou `--ator reciclagem` (em qualquer das duas opções — direto ou SDK). O payload está em `_payloads.py::payload_reciclagem`:

```json
{
    "uverify_template_id": "digitalProductPassport",
    "name": "Reciclagem Pack 75kWh - SR-2031-08-001",
    "issuer": "RecicLar Sorocaba S.A.",
    "gtin": "7891234560044",
    ...
    "cert_pack_credential_tx":   ATOR3_TX,        # tx hash do pack
    "cert_pack_data_hash":       sha256(gtin+serial do Ator 3),
    "cert_celula_credential_tx": ATOR2_TX,        # tx hash da célula
    "cert_celula_data_hash":     sha256(gtin+serial do Ator 2),
    "cert_origem_credential_tx": ATOR1_TX,        # tx hash da origem
    "cert_origem_data_hash":     sha256(gtin+serial do Ator 1)
}
```

A diferença em relação aos outros atores: a recicladora referencia **todas** as credenciais anteriores, não só a imediatamente prévia. Cada referência inclui o par `cert_*_credential_tx` (tx hash) + `cert_*_data_hash` (sha256(gtin+serial) do ator referenciado) — o data_hash é essencial para que o verificador consiga localizar credenciais emitidas via UVerify (Opções B/C). Após a reciclagem o pack deixa de existir; o DPP de reciclagem se torna o ponteiro definitivo para tudo o que veio antes.

### 4.3 Ciclo completo — diagrama

```
[MineraLitio]  --tx1-->  [CellTech]  --tx2-->  [PackMontadora]
     MG                     BA                      SP
      |                      |                       |
      |                      |                       v
      |                      |                 [Veiculo EV]
      |                      |                       |
      |                      |                       v
      |                      |                 (vida util ~10 anos)
      |                      |                       |
      v                      v                       v
      +----------------------+------------> [RecicLar] --tx4
                   todas referenciadas em tx4
```

A cadeia forma um grafo acíclico verificável por qualquer parte — desde o regulador europeu que quer checar elegibilidade ao EU Battery Regulation, até o estudante que está fazendo TCC sobre circularidade.

## Seção 5 — Troubleshooting

### 5.1 "Faucet lento / tADA não chegou"

- Normal levar 1--3 min.  
- Se \> 5 min: confirme rede da carteira \= preprod (não mainnet, não preview).  
- Peça tADA ao instrutor.

### 5.2 "Carteira não sincroniza"

- Eternl: *Settings → Network → Re-sync*.  
- Lace: alternar `Mainnet → Preprod` força ressync.  
- Último recurso: reimportar a seed em nova extensão.

### 5.3 "Network mismatch" / 403 Forbidden no PyCardano

Erro típico do `blockfrost-python`: `ApiError: 403 ... project does not match network`.

- Blockfrost project deve ser **preprod** (project ID começa com `preprod`).  
- `cliente_blockfrost.py` usa `ApiUrls.preprod.value` (`https://cardano-preprod.blockfrost.io/api/v0`). Não troque para `ApiUrls.mainnet` ou `ApiUrls.preview`.  
- Nunca misture um project ID `mainnet` com transações preprod — vai falhar silenciosamente em alguns endpoints.

### 5.4 Rate limit Blockfrost (plano free)

- Free: 10 req/s, 100k req/dia.  
- Se aparecer HTTP 429: espere 60 s, reduza paralelismo.  
- Para o verificador (3 chamadas sequenciais) nunca estoura.

### 5.5 "Credencial UVerify não aparece na verificação"

- Aguarde **1 bloco** (\~20 s em preprod).  
- Confira o tx hash em `https://preprod.cexplorer.io/tx/<hash>` — se o Cexplorer não achou, o Blockfrost também não acha.  
- O endpoint `GET /verify/{data-hash}` do UVerify usa o **data hash** (sha256(gtin+serial)), não o tx hash. 

### 5.6 "ParserCredencial não encontra `uverify_template_id`"

- A transação que você passou não tem metadados UVerify.  
- Confirme que copiou o tx hash certo (não o bloco, não o data hash).  
- Cheque no Cexplorer a aba *Metadata* — o campo deve estar lá literal.

### 5.7 `pycardano` não instala / erro de build de dependência

- O `pycardano` traz dependências nativas (criptografia). Em macOS/Linux geralmente "só funciona"; em Windows pode pedir o [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).  
- Garanta Python **3.11+** (`python3 --version`). 3.10 e abaixo não são suportados pelas versões recentes do `pycardano`.  
- Se `uv sync` falhar com erro de timeout, rode `uv self update` e repita.

### 5.8 `ImportError: cannot import name 'CBORDecodeValueError' from 'cbor2'`

Ocorre quando o `cbor2pure` (dep transitiva do `pycardano`) puxa uma versão recente demais do `cbor2`. O `pyproject.toml` já trava `cbor2<6` para evitar isso. Se mesmo assim aparecer, force a versão:

```shell
uv add "cbor2<6" --upgrade
```

### 5.9 Erros específicos da Opção B (UVerify SDK)

- `UVerifyValidationError: A sign_tx callback is required` — esqueceu de passar `sign_tx=...` para `issue_certificates` (ou para o construtor do `UVerifyClient`).  
- `UVerifyApiError 400` — payload inválido. Confira que **todos** os valores de `metadata` são strings, e que `uverify_template_id` está exato.  
- `UVerifyApiError 403` — endereço sem tADA na rede preprod. Volte ao faucet (Seção 0.3).  
- **Endereço derivado "errado" / não bate com Eternl** — confira que o Eternl está em **preprod**, não preview, não mainnet. As três redes derivam endereços diferentes a partir do mesmo seed.

### 5.10 Erros específicos da Opção A (emissor direto)

- `InsufficientUTxOBalance` — carteira sem tADA. Faucet.  
- `TransactionFailed: BadInputs` — você acabou de submeter uma tx e está tentando outra antes do bloco confirmar. Espere \~20-40s.  
- **Metadata recusada com erro de tamanho** — algum valor do payload tem mais de 64 bytes (limite Cardano). Os payloads do workshop já estão dimensionados; se você customizar, mantenha cada string ≤ 64 chars ou divida em lista de strings.

### 5.11 `RecursionError` ao verificar credenciais UVerify

```
RecursionError: maximum recursion depth exceeded
```

Ocorre quando o verificador tenta parsear a resposta JSON da API UVerify usando o SDK Python (`verify_by_transaction`). A resposta inclui um campo `stateDatum` profundamente aninhado (centenas de níveis de histórico do smart contract), que excede o limite de recursão do CPython — mesmo com `sys.setrecursionlimit(10000)`, pois o parser JSON em C tem limite próprio.

**Solução:** o `verificador.py` já contorna isso fazendo uma chamada HTTP direta à API (`/api/v1/verify/by-transaction-hash/{tx}/{dh}`) e extraindo apenas o campo `extra` (onde fica a metadata) via regex, sem parsear o JSON inteiro. Se você estiver escrevendo código customizado, evite usar `verify_by_transaction()` do SDK e use a abordagem HTTP direta.

### 5.12 Verificador retorna 404 para credencial emitida via UVerify (SDK ou UI)

```
UVerifyApiError: UVerify API error 404
```

Significa que o verificador não encontrou a credencial na API do UVerify. Causas mais comuns:

- **`data_hash` errado** — a API do UVerify busca por `data_hash` (= `sha256(gtin + serial)`), não pelo tx hash. Se o `data_hash` usado na busca não corresponde ao que foi usado na emissão, retorna 404.
- **Credencial emitida pela UI** — quando emitida pela UI do UVerify, o `data_hash` pode diferir do calculado por `sha256(gtin + serial)` se os campos foram preenchidos com valores ligeiramente diferentes (espaços, acentos, etc). Verifique a URL de verificação na tela de sucesso do UVerify (formato: `https://app.preprod.uverify.io/verify/<data_hash>/<index>?serial=<serial>`).
- **Campos `cert_*_data_hash` ausentes nos payloads** — em cadeias mistas (A + B/C), cada credencial precisa carregar o `cert_*_data_hash` do ator que referencia. Sem esse hint, o verificador tenta extrair o hash do redeemer on-chain (mais lento) ou do inline datum (menos confiável). Confira que `_payloads.py` inclui esses campos.
- **Blockfrost ainda não indexou** — após emissão, aguarde pelo menos 1 bloco (~20-40s em preprod) antes de verificar. Se acabou de emitir e recebe 404, espere e tente novamente. 
