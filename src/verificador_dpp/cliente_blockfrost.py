"""Wrapper enxuto em torno do PyCardano + Blockfrost.

Expoe apenas o que precisamos: buscar metadados de uma transacao.
Trabalha em PREPROD (onde o UVerify publico opera).
"""

from blockfrost import ApiUrls
from pycardano import BlockFrostChainContext


class ClienteBlockfrost:
    """Wrapper de leitura sobre o BlockFrostChainContext do PyCardano."""

    PREPROD_URL = ApiUrls.preprod.value  # https://cardano-preprod.blockfrost.io/api/v0

    def __init__(self, project_id: str) -> None:
        # PyCardano expoe o cliente blockfrost-python em `.api`.
        # Usamos esse acesso direto porque a leitura de metadados nao
        # depende do contexto de assinatura/submissao do PyCardano.
        self._context = BlockFrostChainContext(
            project_id=project_id,
            base_url=self.PREPROD_URL,
        )

    def buscar_metadados(self, tx_hash: str) -> list:
        """Busca os metadados JSON associados a um hash de transacao.

        O Blockfrost retorna uma lista: uma entrada por label de metadata
        presente na transacao. Cada entrada tem `label`, `json_metadata`
        e `cbor_metadata`.
        """
        return self._context.api.transaction_metadata(tx_hash)
