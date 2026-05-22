"""Parser de credenciais UVerify a partir de metadados Cardano.

Este modulo e responsavel por ler os metadados nativos de uma transacao
Cardano (obtidos via Blockfrost) e converter para um objeto CredencialDPP.

Contexto:
    Quando uma credencial e emitida pelo `emissor_direto` (opcao A), os
    dados do DPP sao gravados diretamente na transacao como metadata
    nativa do Cardano, sob o label 1990. Os metadados incluem o campo
    `uverify_template_id` para identificar que e uma credencial UVerify.

    O Blockfrost retorna esses metadados como uma lista de entradas
    (uma por label), onde cada entrada e um Namespace do blockfrost-python
    (nao um dict). Este parser normaliza esses Namespace objects e
    procura recursivamente pelo campo `uverify_template_id`.

Fluxo:
    1. Receber lista de metadados do Blockfrost
    2. Para cada entrada, normalizar Namespace → dict
    3. Buscar recursivamente um dict com `uverify_template_id`
    4. Converter os campos encontrados para CredencialDPP
"""

from typing import Any

from .modelos import CredencialDPP

# O template DPP padrao usado por todas as credenciais do workshop.
TEMPLATE_DPP = "digitalProductPassport"


class ParserCredencial:
    """Converte metadados brutos do Blockfrost em objetos CredencialDPP.

    Uso:
        parser = ParserCredencial()
        metadados = blockfrost.transaction_metadata(tx_hash)
        credencial = parser.extrair_credencial(metadados)
    """

    def extrair_credencial(self, metadados: list) -> CredencialDPP:
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
                return self._converter(credencial)

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

    def _converter(self, n: dict) -> CredencialDPP:
        """Converte um dict de metadata UVerify para CredencialDPP.

        Classifica os campos do payload pela convencao de nomes:
          - cert_*_credential_tx → referencias (links para outras txs)
          - cert_*_data_hash     → data_hashes (hints para lookup UVerify)
          - mat_*                → materiais (composicao do produto)
          - campos padrao        → mapeados diretamente (name, gtin, etc)

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
        referencias: dict[str, str] = {}
        materiais: dict[str, str] = {}
        data_hashes: dict[str, str] = {}

        for chave, valor in n.items():
            if chave.startswith("cert_") and chave.endswith("_credential_tx"):
                # Ex: "cert_origem_credential_tx" → "origem_credential_tx"
                # Remove o prefixo "cert_" para simplificar o acesso.
                referencias[chave[len("cert_"):]] = str(valor)
            elif chave.startswith("cert_") and chave.endswith("_data_hash"):
                # Ex: "cert_origem_data_hash" → "origem_data_hash"
                data_hashes[chave[len("cert_"):]] = str(valor)
            elif chave.startswith("mat_"):
                # Ex: "mat_niquel" → "niquel"
                materiais[chave[len("mat_"):]] = str(valor)

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
        )

    @staticmethod
    def _texto(n: dict, campo: str) -> str | None:
        """Extrai um campo como string, retornando None se ausente."""
        v = n.get(campo)
        return None if v is None else str(v)
