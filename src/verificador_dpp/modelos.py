"""Records de dominio do verificador DPP.

Define as estruturas de dados usadas por todo o verificador:

  - CredencialDPP: uma credencial individual extraida da blockchain
    (pode vir de metadata nativa ou da API UVerify).

  - PassaporteBateria: agrupa as tres credenciais da cadeia
    (origem → celula → pack) para gerar o relatorio consolidado.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CredencialDPP:
    """Credencial DPP extraida de metadados UVerify em Cardano.

    Cada credencial representa um elo na cadeia de suprimentos
    da bateria (ex: origem do litio, fabricacao de celulas, montagem
    do pack). Os dados sao extraidos de metadata nativa Cardano
    (opcao A) ou da API do UVerify (opcoes B/C).

    Atributos:
        nome:               nome do produto (campo "name" do payload)
        emitente:           empresa emissora (campo "issuer")
        gtin:               GTIN — codigo de barras global do produto
        origem:             local de fabricacao/extracao (campo "origin")
        fabricado_em:       data de fabricacao ISO 8601 (campo "manufactured")
        pegada_carbono:     emissoes de CO2 (campo "carbon_footprint")
        conteudo_reciclado: percentual reciclado (campo "recycled_content")
        materiais:          composicao do produto — extraido dos campos
                            "mat_*" (ex: mat_niquel → {"niquel": "80%"})
        referencias:        links para outras credenciais na cadeia — extraido
                            dos campos "cert_*_credential_tx"
                            (ex: cert_origem_credential_tx → tx_hash).
                            Analogia: como "ponteiros" para os certificados
                            anteriores na cadeia de suprimentos.
        data_hashes:        impressoes digitais (sha256(gtin+serial)) dos
                            produtos referenciados — extraido dos campos
                            "cert_*_data_hash". Necessarios para encontrar
                            credenciais emitidas via SDK ou UI na API UVerify.
    """

    nome: str | None
    emitente: str | None
    gtin: str | None
    origem: str | None
    fabricado_em: str | None
    pegada_carbono: str | None
    conteudo_reciclado: str | None
    materiais: dict[str, str]
    referencias: dict[str, str]
    data_hashes: dict[str, str]


@dataclass(frozen=True)
class PassaporteBateria:
    """Passaporte consolidado: as tres credenciais encadeadas da cadeia.

    Agrupa os tres elos da cadeia de suprimentos verificados:
        origem: Ator 1 — extracao do litio (MineraLitio)
        celula: Ator 2 — fabricacao das celulas (CellTech)
        pack:   Ator 3 — montagem do pack de bateria (PackMontadora)

    Qualquer elo pode ser None se nao foi encontrado na cadeia
    (o relatorio exibe um aviso nesses casos).

    Analogia: como um "dossiê completo" do produto — junta todos
    os certificados desde a materia-prima ate o produto final.
    """

    origem: CredencialDPP | None
    celula: CredencialDPP | None
    pack: CredencialDPP | None
