"""Parser de credenciais UVerify a partir de metadados Cardano.

O UVerify escreve em um label de metadata que contem, entre outros
campos, "uverify_template_id". Aqui procuramos a primeira entrada
que bate com esse padrao e a convertemos para CredencialDPP.
"""

from typing import Any

from .modelos import CredencialDPP

TEMPLATE_DPP = "digitalProductPassport"


class ParserCredencial:
    def extrair_credencial(self, metadados: list) -> CredencialDPP:
        if not metadados:
            raise ValueError(
                "Transacao nao possui metadados - nao e uma credencial UVerify."
            )

        # O UVerify pode publicar em mais de um label. Varremos todos
        # procurando uma estrutura que contenha uverify_template_id.
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
        """blockfrost-python devolve Namespace; convertemos para dict/list nativo."""
        valor = getattr(entrada, "json_metadata", entrada)
        return self._normalizar(valor)

    def _normalizar(self, valor: Any) -> Any:
        if hasattr(valor, "__dict__") and not isinstance(valor, (str, bytes)):
            return {k: self._normalizar(v) for k, v in vars(valor).items()}
        if isinstance(valor, dict):
            return {k: self._normalizar(v) for k, v in valor.items()}
        if isinstance(valor, list):
            return [self._normalizar(v) for v in valor]
        return valor

    def _localizar_credencial_uverify(self, no: Any) -> dict | None:
        """Busca recursiva por um objeto com `uverify_template_id`.

        Tolera variacoes no label/estrutura exata usados pelo UVerify
        ao longo do tempo.
        """
        if no is None:
            return None
        if isinstance(no, dict):
            if "uverify_template_id" in no:
                return no
            for filho in no.values():
                achado = self._localizar_credencial_uverify(filho)
                if achado is not None:
                    return achado
        elif isinstance(no, list):
            for filho in no:
                achado = self._localizar_credencial_uverify(filho)
                if achado is not None:
                    return achado
        return None

    def _converter(self, n: dict) -> CredencialDPP:
        template_id = n.get("uverify_template_id") or ""
        if str(template_id).lower() != TEMPLATE_DPP.lower():
            raise ValueError(
                f"Template desconhecido: '{template_id}'. "
                f"Esperado '{TEMPLATE_DPP}'."
            )

        # Referencias a outras credenciais ficam em cert_* (certifications)
        # conforme a convencao do workshop:
        #   cert_origem_credential_tx
        #   cert_celula_credential_tx
        referencias: dict[str, str] = {}
        materiais: dict[str, str] = {}

        for chave, valor in n.items():
            if chave.startswith("cert_") and chave.endswith("_credential_tx"):
                referencias[chave[len("cert_"):]] = str(valor)
            elif chave.startswith("mat_"):
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
        )

    @staticmethod
    def _texto(n: dict, campo: str) -> str | None:
        v = n.get(campo)
        return None if v is None else str(v)
