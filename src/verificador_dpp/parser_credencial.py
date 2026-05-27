"""Parser de credenciais UVerify a partir de metadados Cardano.

Este modulo le os metadados nativos de uma transacao Cardano
(obtidos via Blockfrost) e converte para um objeto CredencialDPP.

Analogia: o Blockfrost devolve os dados "crus" da blockchain (como
um documento escaneado). Este parser "le" esse documento, encontra
o certificado DPP dentro dele (identificado pelo campo
`uverify_template_id`), e organiza os dados em campos estruturados.

Fluxo:
    1. Receber lista de metadados do Blockfrost
    2. Para cada entrada, normalizar Namespace → dict
       (o Blockfrost retorna objetos especiais, nao dicts)
    3. Buscar recursivamente um dict com `uverify_template_id`
    4. Converter os campos encontrados para CredencialDPP
"""

from typing import Any

from .modelos import CredencialDPP

# O template DPP padrao usado por todas as credenciais do workshop.
TEMPLATE_DPP = "digitalProductPassport"


def classificar_campos(meta: dict) -> tuple[dict, dict, dict]:
    """Classifica campos de metadata por prefixo.

    Convencao UVerify:
      - ref_*_tx       → referencias (links/"ponteiros" para outras txs)
      - ref_*_data_hash → data_hashes (impressoes digitais para lookup UVerify)
      - mat_*           → materiais (composicao do produto)

    Returns:
        Tupla (referencias, data_hashes, materiais).
    """
    referencias: dict[str, str] = {}
    data_hashes: dict[str, str] = {}
    materiais: dict[str, str] = {}
    for k, v in meta.items():
        if k.startswith("ref_") and k.endswith("_tx"):
            referencias[k[len("ref_"):]] = str(v)
        elif k.startswith("ref_") and k.endswith("_data_hash"):
            data_hashes[k[len("ref_"):]] = str(v)
        elif k.startswith("mat_"):
            materiais[k[len("mat_"):]] = str(v)
    return referencias, data_hashes, materiais


class ParserCredencial:
    """Converte metadados brutos do Blockfrost em objetos CredencialDPP.

    Analogia: funciona como um "leitor de formularios" — recebe os
    dados crus da blockchain e extrai os campos do certificado DPP.

    Uso:
        parser = ParserCredencial()
        metadados = blockfrost.transaction_metadata(tx_hash)
        credencial = parser.extrair_credencial(metadados)
    """

    def extrair_credencial(
        self, metadados: list, tx_hash: str | None = None,
    ) -> CredencialDPP:
        """Extrai a credencial UVerify de uma lista de metadados.

        Percorre todos os labels da transacao procurando um que contenha
        o campo `uverify_template_id`. Quando encontra, converte para
        CredencialDPP.

        Parametros:
            metadados: lista de entradas retornada por
                       blockfrost.transaction_metadata(tx_hash)

        Retorna:
            CredencialDPP com os dados extraidos.

        Levanta:
            ValueError: se nao houver metadados ou se nenhum label
                        contiver uma credencial UVerify.
        """
        if not metadados:
            raise ValueError(
                "Transacao nao possui metadados - nao e uma credencial UVerify."
            )

        # Percorre cada label de metadata da transacao.
        # Uma tx pode ter metadata em varios labels; varremos todos
        # procurando o que contem uverify_template_id.
        for entrada in metadados:
            json_metadata = self._extrair_json(entrada)
            credencial = self._localizar_credencial_uverify(json_metadata)
            if credencial is not None:
                return self._converter(credencial, tx_hash=tx_hash)

        raise ValueError(
            "Nenhum label desta transacao contem uma credencial UVerify "
            "(campo 'uverify_template_id' nao encontrado)."
        )

    def _extrair_json(self, entrada: Any) -> Any:
        """Extrai e normaliza o JSON de uma entrada de metadata.

        O Blockfrost retorna cada entrada com um atributo `json_metadata`
        (que e um Namespace, nao um dict). Esta funcao extrai esse
        atributo e converte recursivamente para tipos Python nativos.
        """
        valor = getattr(entrada, "json_metadata", entrada)
        return self._normalizar(valor)

    def _normalizar(self, valor: Any) -> Any:
        """Converte recursivamente Namespace objects para dicts/lists.

        O blockfrost-python retorna objetos do tipo Namespace (que se
        parecem com dicts mas nao sao). Esta funcao percorre a estrutura
        inteira e converte tudo para tipos Python nativos (dict, list,
        str, int, etc), para que possamos trabalhar com eles normalmente.

        Analogia: como "traduzir" um documento de um formato proprietario
        para um formato padrao que qualquer programa consegue ler.

        Exemplos:
            Namespace(name="Litio") → {"name": "Litio"}
            [Namespace(a=1)]        → [{"a": 1}]
        """
        # Se e um Namespace (tem __dict__ mas nao e string/bytes),
        # converte para dict e normaliza cada valor recursivamente.
        if hasattr(valor, "__dict__") and not isinstance(valor, (str, bytes)):
            return {k: self._normalizar(v) for k, v in vars(valor).items()}
        # Se ja e um dict, normaliza os valores.
        if isinstance(valor, dict):
            return {k: self._normalizar(v) for k, v in valor.items()}
        # Se e uma lista, normaliza cada item.
        if isinstance(valor, list):
            return [self._normalizar(v) for v in valor]
        # Caso base: strings, numeros, None, etc — retorna como esta.
        return valor

    def _localizar_credencial_uverify(self, no: Any) -> dict | None:
        """Busca recursiva por um dict que contenha `uverify_template_id`.

        Percorre a estrutura inteira (dicts aninhados, listas) ate
        encontrar o primeiro dict com a chave `uverify_template_id`.
        Isso tolera variacoes na estrutura que o UVerify pode usar.

        Retorna:
            O dict com a credencial, ou None se nao encontrar.
        """
        if no is None:
            return None
        if isinstance(no, dict):
            # Achamos! Este dict tem o campo identificador.
            if "uverify_template_id" in no:
                return no
            # Se nao, procura nos valores deste dict.
            for filho in no.values():
                achado = self._localizar_credencial_uverify(filho)
                if achado is not None:
                    return achado
        elif isinstance(no, list):
            # Procura em cada item da lista.
            for filho in no:
                achado = self._localizar_credencial_uverify(filho)
                if achado is not None:
                    return achado
        return None

    def _converter(
        self, n: dict, tx_hash: str | None = None,
    ) -> CredencialDPP:
        """Converte um dict de metadata UVerify para CredencialDPP.

        Classifica os campos do payload pela convencao de nomes:
          - ref_*_tx       → referencias (links/"ponteiros" para outras txs)
          - ref_*_data_hash → data_hashes (impressoes digitais para lookup UVerify)
          - mat_*           → materiais (composicao do produto)
          - campos padrao   → mapeados diretamente (name, gtin, etc)

        Levanta:
            ValueError: se o template nao for `digitalProductPassport`.
        """
        # Validar que o template e o esperado.
        template_id = n.get("uverify_template_id") or ""
        if str(template_id).lower() != TEMPLATE_DPP.lower():
            raise ValueError(
                f"Template desconhecido: '{template_id}'. "
                f"Esperado '{TEMPLATE_DPP}'."
            )

        # Classificar cada campo pelo prefixo do nome.
        referencias, data_hashes, materiais = classificar_campos(n)

        return CredencialDPP(
            nome=self._texto(n, "name"),
            emitente=self._texto(n, "issuer"),
            gtin=self._texto(n, "gtin"),
            origem=self._texto(n, "origin"),
            fabricado_em=self._texto(n, "manufactured"),
            pegada_carbono=self._texto(n, "carbon_footprint"),
            conteudo_reciclado=self._texto(n, "recycled_content"),
            materiais=materiais,
            referencias=referencias,
            data_hashes=data_hashes,
            tx_hash=tx_hash,
            metodo_emissao="metadata",
        )

    @staticmethod
    def _texto(n: dict, campo: str) -> str | None:
        """Extrai um campo como string, retornando None se ausente."""
        v = n.get(campo)
        return None if v is None else str(v)
