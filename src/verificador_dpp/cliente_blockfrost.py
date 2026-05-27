"""Wrapper enxuto em torno do PyCardano + Blockfrost.

Encapsula o acesso a blockchain Cardano via API do Blockfrost e
expoe metodos de consulta de metadata nativa de transacoes.

Analogia: o Blockfrost funciona como um "portal de consulta" ao
cartorio (blockchain) — em vez de rodar um nó Cardano completo,
usamos a API do Blockfrost para ler os registros publicos.

Trabalha em PREPROD (rede de testes / testnet).
"""

from blockfrost import ApiUrls
from pycardano import BlockFrostChainContext


class ClienteBlockfrost:
    """Cliente Blockfrost para leitura de metadata nativa Cardano.

    Usa o BlockFrostChainContext do PyCardano para se conectar a rede
    preprod (testnet). Analogia: como abrir uma sessao no portal do
    cartorio — a partir daqui podemos consultar qualquer transacao.
    """

    PREPROD_URL = ApiUrls.preprod.value  # https://cardano-preprod.blockfrost.io/api/v0

    def __init__(self, project_id: str) -> None:
        # Conecta ao Blockfrost preprod usando o project_id do .env.
        # O BlockFrostChainContext e a abstracao do PyCardano que
        # encapsula chamadas REST a API do Blockfrost.
        self._context = BlockFrostChainContext(
            project_id=project_id,
            base_url=self.PREPROD_URL,
        )

    def buscar_metadados(self, tx_hash: str) -> list:
        """Busca a metadata nativa de uma transacao Cardano pelo tx_hash.

        Metadata nativa e o campo de dados livre que qualquer transacao
        Cardano pode carregar (labels numericos, cada um com um JSON).
        Analogia: como pedir ao cartorio o "anexo" de um documento
        registrado — o tx_hash e o numero de protocolo.

        Retorna uma lista de entradas (uma por label de metadata).
        Se a transacao nao tiver metadata nativa, retorna lista vazia.
        """
        return self._context.api.transaction_metadata(tx_hash)
