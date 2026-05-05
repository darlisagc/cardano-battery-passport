"""Records de domínio do verificador DPP."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CredencialDPP:
    """Credencial DPP extraida de metadados UVerify em Cardano.

    Atributos:
        nome:               name
        emitente:           issuer
        gtin:               GTIN (Global Trade Item Number)
        origem:             origin (pais ou regiao)
        fabricado_em:       manufactured (ISO 8601)
        pegada_carbono:     carbon_footprint
        conteudo_reciclado: recycled_content
        materiais:          chaves extraidas de "mat_*"
        referencias:        chaves extraidas de "cert_*_credential_tx"
                            (encadeamento com outras credenciais DPP)
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


@dataclass(frozen=True)
class PassaporteBateria:
    """Passaporte consolidado: as tres credenciais encadeadas da cadeia
    (origem do litio, celula, pack).
    """

    origem: CredencialDPP | None
    celula: CredencialDPP | None
    pack: CredencialDPP | None
