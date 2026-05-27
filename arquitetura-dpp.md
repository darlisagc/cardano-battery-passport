# Arquitetura do Passaporte Digital de Produto (DPP) — Bateria EV

Este documento descreve a arquitetura do sistema de rastreabilidade de baterias EV
sobre a blockchain Cardano. Cada diagrama pode ser visualizado em qualquer
ferramenta compativel com Mermaid (GitHub, VS Code, mermaid.live, etc.).

---

## 1. Cadeia de Suprimentos

A cadeia de suprimentos e composta por 4 atores. Cada ator emite uma credencial
na blockchain Cardano e referencia a credencial do ator anterior por meio dos
campos `cert_*_credential_tx` (tx hash) e `cert_*_data_hash` (impressao digital
SHA-256 para lookup UVerify). O verificador percorre essa cadeia **de tras para
frente** (pack &rarr; celula &rarr; origem) para montar o Passaporte da Bateria.

```mermaid
flowchart LR
    subgraph A1["MineraLitio"]
        direction TB
        a1p["Lote Litio Jequitinhonha 2026-03"]
        a1l["Aracuai, MG, BR"]
        a1s["Serial: ML-JQT-2026-03-042"]
    end

    subgraph A2["CellTech"]
        direction TB
        a2p["Celulas NMC 811 - Lote BA-2026-04-008"]
        a2l["Camacari, BA, BR"]
        a2s["Serial: CT-BA-2026-04-008"]
    end

    subgraph A3["PackMontadora"]
        direction TB
        a3p["Pack EV 75kWh - SP-2026-04-155"]
        a3l["Sao Bernardo do Campo, SP, BR"]
        a3s["Serial: PM-SP-2026-04-155"]
    end

    subgraph A4["RecicLar"]
        direction TB
        a4p["Reciclagem Pack 75kWh - SR-2031-08-001"]
        a4l["Sorocaba, SP, BR"]
        a4s["Serial: RL-SR-2031-08-001"]
    end

    A1 -- "cert_origem_credential_tx\ncert_origem_data_hash" --> A2
    A2 -- "cert_celula_credential_tx\ncert_celula_data_hash" --> A3
    A3 -- "cert_pack_credential_tx\ncert_pack_data_hash" --> A4

    A1 -. "cert_origem_credential_tx\ncert_origem_data_hash" .-> A4
    A2 -. "cert_celula_credential_tx\ncert_celula_data_hash" .-> A4

    style A1 fill:#d4edda,stroke:#28a745
    style A2 fill:#cce5ff,stroke:#007bff
    style A3 fill:#fff3cd,stroke:#ffc107
    style A4 fill:#f8d7da,stroke:#dc3545
```

**Legenda de cores:**
- Verde — Mineracao (origem da materia-prima)
- Azul — Fabricacao de celulas
- Amarelo — Montagem do pack
- Vermelho — Reciclagem (fim de vida)

> **Nota:** RecicLar referencia os 3 atores anteriores
> (`cert_origem_*`, `cert_celula_*`, `cert_pack_*`),
> permitindo rastreabilidade completa em uma unica consulta.
> Cada referencia inclui o par `_credential_tx` (tx hash na blockchain)
> e `_data_hash` (sha256(gtin+serial) para lookup na API UVerify).

---

## 2. As 3 Opcoes de Emissao (A, B e C)

O sistema oferece 3 caminhos para emitir uma credencial DPP na blockchain Cardano.
Todos partem do mesmo payload definido em `_payloads.py` e resultam em uma
transacao confirmada na rede preprod.

```mermaid
flowchart TB
    PL["_payloads.py\npayload_origem() / payload_celula() / payload_pack()"]

    subgraph OpcaoA["Opcao A — PyCardano Direto"]
        direction TB
        wa["wallet.py\ncarregar_carteira(mnemonic)"]
        tb["TransactionBuilder\nAuxiliaryData + Metadata"]
        ml["label 1990 = payload completo"]
        bf_a["Blockfrost API\nsubmit(tx_signed)"]
        ca["Cardano Preprod\nmetadata nativa no label 1990"]
    end

    subgraph OpcaoB["Opcao B — UVerify SDK"]
        direction TB
        wb["wallet.py\ncarregar_carteira(mnemonic)"]
        cd["CertificateData\nhash=SHA256(gtin+serial)\nmetadata=payload"]
        sdk["UVerifyClient\nissue_certificates()"]
        cb["sign_tx callback\nassinar com payment_skey"]
        cc["Cardano Preprod\ninline datum + redeemer"]
    end

    subgraph OpcaoC["Opcao C — UVerify Web UI"]
        direction TB
        ui["app.preprod.uverify.io\nTemplate: Digital Product Passport"]
        wc["Wallet do navegador\nassinar transacao"]
        ccc["Cardano Preprod\ninline datum + redeemer"]
    end

    PL --> wa
    wa --> tb
    tb --> ml
    ml --> bf_a
    bf_a --> ca

    PL --> wb
    wb --> cd
    cd --> sdk
    sdk --> cb
    cb --> cc

    PL -.-> ui
    ui --> wc
    wc --> ccc

    style OpcaoA fill:#d4edda,stroke:#28a745
    style OpcaoB fill:#cce5ff,stroke:#007bff
    style OpcaoC fill:#e2d5f1,stroke:#6f42c1
```

### Resumo das diferencas

| Aspecto | Opcao A | Opcao B | Opcao C |
|---------|---------|---------|---------|
| **Modulo** | `emissor_direto.py` | `emissor_sdk.py` | UI web |
| **Armazenamento on-chain** | Metadata nativa (label 1990) | Inline datum + redeemer | Inline datum + redeemer |
| **Onde fica o payload** | Direto na metadata da tx | Servidor UVerify (off-chain) | Servidor UVerify (off-chain) |
| **Assinatura** | PyCardano `build_and_sign()` | Callback `sign_tx` via SDK | Wallet no navegador |
| **Dependencia externa** | Apenas Blockfrost | Blockfrost + UVerify SDK | UVerify Web |

---

## 3. Fluxo do Verificador

O verificador (`verificador.py`) recebe o `TX_HASH_PACK` como ponto de entrada
e percorre a cadeia de referencias de tras para frente. Para cada credencial,
a funcao `buscar_credencial()` tenta dois caminhos de leitura: metadata nativa
(Opcao A) e API publica UVerify (Opcoes B/C).

```mermaid
sequenceDiagram
    participant V as verificador.py
    participant BF as Blockfrost API
    participant PC as ParserCredencial
    participant UV as UVerify API (HTTP direto)
    participant R as RelatorioPassaporte

    Note over V: Passo 1/4 — Buscar credencial do Pack
    Note over V: buscar_credencial(tx=TX_HASH_PACK, hint=DATA_HASH_PACK)
    V->>BF: transaction_metadata(TX_HASH_PACK)
    alt Caminho 1 — Metadata nativa encontrada (Opcao A)
        BF-->>V: metadados com label 1990
        V->>PC: extrair_credencial(metadados)
        PC-->>V: CredencialDPP (pack)
    else Caminho 2 — Sem metadata nativa (Opcoes B/C)
        Note over V: Reunir candidatos data_hash de 3 fontes
        Note over V: 1. hint (DATA_HASH_PACK do .env)
        V->>BF: transaction_redeemers(tx_hash)
        Note over V: 2. _extrair_hashes_do_redeemer()
        V->>BF: transaction_utxos(tx_hash)
        Note over V: 3. _walk_for_32byte() no inline datum
        V->>UV: GET /api/v1/verify/{data_hash}
        UV-->>V: JSON com metadata do certificado
        Note over V: _verify_by_transaction_direct()
        V-->>V: CredencialDPP (pack) + data_hashes
    end

    Note over V: Passo 2/4 — Seguir referencia para Celula
    Note over V: tx = cred_pack.referencias["celula_credential_tx"]
    Note over V: hint = cred_pack.data_hashes["celula_data_hash"]
    V->>BF: transaction_metadata(tx_hash_celula)
    alt Caminho 1 — Metadata nativa (Opcao A)
        BF-->>V: metadados
        V->>PC: extrair_credencial(metadados)
        PC-->>V: CredencialDPP (celula)
    else Caminho 2 — UVerify (Opcoes B/C)
        Note over V: Fontes: hint + redeemer + inline datum
        V->>UV: GET /api/v1/verify/{data_hash}
        UV-->>V: CredencialDPP (celula) + data_hashes
    end

    Note over V: Passo 3/4 — Seguir referencia para Origem
    Note over V: tx = cred_celula.referencias["origem_credential_tx"]
    Note over V: hint = cred_celula.data_hashes["origem_data_hash"]
    V->>BF: transaction_metadata(tx_hash_origem)
    alt Caminho 1 — Metadata nativa (Opcao A)
        BF-->>V: metadados
        V->>PC: extrair_credencial(metadados)
        PC-->>V: CredencialDPP (origem)
    else Caminho 2 — UVerify (Opcoes B/C)
        V->>UV: GET /api/v1/verify/{data_hash}
        UV-->>V: CredencialDPP (origem)
    end

    Note over V: Passo 4/4 — Montar Passaporte e gerar relatorio
    V->>V: PassaporteBateria(origem, celula, pack)
    V->>R: gerar(passaporte)
    R-->>V: Relatorio em portugues
```

### Os dois caminhos de leitura por credencial

Para **cada** credencial encontrada na cadeia, `buscar_credencial()` tenta:

1. **Caminho 1 (metadata nativa):** consulta `Blockfrost.transaction_metadata()`,
   procura por entrada com `uverify_template_id`, converte via
   `ParserCredencial.extrair_credencial()` em `CredencialDPP`.

2. **Caminho 2 (UVerify API):** reune candidatos a `data_hash` de **3 fontes**,
   em ordem de confiabilidade:
   - **(a) Hint** da credencial anterior na cadeia (campo `cert_*_data_hash`
     no payload, propagado via `CredencialDPP.data_hashes`) — atalho direto.
   - **(b) Redeemer on-chain** — `_extrair_hashes_do_redeemer()` navega a
     estrutura `UVerifyStateRedeemer.fields[1].list[*].fields[0].bytes`
     para extrair o hash real do certificado.
   - **(c) Inline datum** — `_walk_for_32byte()` varre o CBOR decodificado
     buscando sequencias de 32 bytes (fallback heuristico).

   Para cada candidato, chama `_verify_by_transaction_direct()` que faz
   `GET /api/v1/verify/{data_hash}` diretamente na API publica do UVerify
   (sem usar o SDK, para evitar `RecursionError` causado por respostas
   JSON profundamente aninhadas). O primeiro match valido e convertido em
   `CredencialDPP`.

---

## 4. Estrutura On-Chain

Os dois formatos de transacao coexistem na mesma rede e sao ambos lidos pelo
verificador. Apos o parsing, ambos convergem para a mesma estrutura
`CredencialDPP`.

```mermaid
flowchart TB
    subgraph TxA["Transacao — Opcao A (metadata nativa)"]
        direction TB
        bodyA["TransactionBody\ninputs / outputs"]
        auxA["AuxiliaryData"]
        metaA["Metadata"]
        labelA["Label 1990"]
        payA["Payload completo\nuverify_template_id: digitalProductPassport\nname, issuer, gtin, origin, ...\ncert_origem_credential_tx: tx_hash\ncert_origem_data_hash: sha256\nmat_niquel: 80%\n..."]

        bodyA --- auxA
        auxA --- metaA
        metaA --- labelA
        labelA --- payA
    end

    subgraph TxBC["Transacao — Opcoes B/C (UVerify smart contract)"]
        direction TB
        bodyBC["TransactionBody\ninputs / outputs / script_ref"]
        outBC["Script Output"]
        datumBC["Inline Datum (CBOR)\nstate datum do smart contract\nsequencias de 32 bytes (candidatos)"]
        redBC["Redeemer (UVerifyStateRedeemer)\nfields[1].list[*].fields[0].bytes\n= data_hash real do certificado"]
        witBC["Witnesses\nPlutus script + assinatura"]
        offBC["Servidor UVerify (off-chain)\npayload completo indexado por data_hash\nGET /api/v1/verify/{data_hash}"]

        bodyBC --- outBC
        outBC --- datumBC
        bodyBC --- redBC
        bodyBC --- witBC
        redBC -. "data_hash" .-> offBC
    end

    subgraph Convergencia["Resultado apos parsing"]
        cred["CredencialDPP\nnome / emitente / gtin / origem\nfabricado_em / pegada_carbono\nconteudo_reciclado\nmateriais: dict\nreferencias: dict\ndata_hashes: dict"]
    end

    payA --> cred
    offBC --> cred

    style TxA fill:#d4edda,stroke:#28a745
    style TxBC fill:#cce5ff,stroke:#007bff
    style Convergencia fill:#fff3cd,stroke:#ffc107
```

### Detalhes de cada formato

**Opcao A — metadata nativa:**
- O payload inteiro (todos os campos `name`, `issuer`, `gtin`, `mat_*`, `cert_*`, etc.)
  e armazenado diretamente na metadata da transacao sob o label `1990`.
- Leitura: `Blockfrost.transaction_metadata(tx_hash)` retorna o dict completo.
- Vantagem: auto-contido, nenhuma dependencia externa para verificacao.

**Opcoes B/C — UVerify smart contract:**
- O `data_hash` (SHA-256 de `gtin + serial`) e embarcado no redeemer
  (estrutura `UVerifyStateRedeemer`) e em sequencias de 32 bytes no inline datum.
- O payload completo fica armazenado off-chain no servidor UVerify, acessivel via
  `GET /api/v1/verify/{data_hash}`.
- Leitura: extrair `data_hash` do redeemer (fonte confiavel) ou do inline datum
  (fallback heuristico), depois consultar a API publica do UVerify.
- Vantagem: transacao menor on-chain; dados sensiveis podem ser controlados off-chain.

**Convergencia:**
Independente do formato, o parser converte o resultado em `CredencialDPP`
(definido em `modelos.py`), com campos uniformes para `materiais`, `referencias`
e `data_hashes`. O `PassaporteBateria` e entao montado a partir de 3 instancias
de `CredencialDPP` (origem, celula, pack). Os `data_hashes` sao propagados de
uma credencial para a proxima como hints para acelerar o lookup UVerify.

---

## Mapa de Arquivos

| Arquivo | Funcao |
|---------|--------|
| `_payloads.py` | Definicao dos 4 atores e funcoes `payload_*()` |
| `wallet.py` | Derivacao HD wallet (CIP-1852) via mnemonic |
| `emissor_direto.py` | Opcao A — emissao com PyCardano + metadata nativa |
| `emissor_sdk.py` | Opcao B — emissao via UVerify SDK + callback de assinatura |
| `verificador.py` | Verificador unificado (A+B+C) com caminhada reversa |
| `parser_credencial.py` | Conversao de metadados brutos em `CredencialDPP` |
| `modelos.py` | Dataclasses: `CredencialDPP`, `PassaporteBateria` |
| `relatorio_passaporte.py` | Geracao do relatorio final em portugues |
| `cliente_blockfrost.py` | Wrapper de leitura para a API Blockfrost |
