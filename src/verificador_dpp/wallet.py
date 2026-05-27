"""Carteira HD compartilhada (CIP-1852).

Deriva a chave de pagamento e o endereco preprod a partir do
mnemonico (24 palavras). Usada pelos dois emissores (direto e SDK).

Analogia: o mnemonico e como uma "senha mestre" — a partir dele,
este modulo gera a chave para assinar transacoes (como uma
assinatura digital) e o endereco da carteira (como um numero
de conta bancaria).

Caminhos CIP-1852: padrao usado por Eternl, Lace e outras carteiras
Cardano — o endereco gerado aqui coincide com o da sua carteira.
"""

from __future__ import annotations

from pycardano import Address, ExtendedSigningKey, HDWallet, Network


def carregar_carteira(mnemonic: str) -> tuple[ExtendedSigningKey, Address]:
    """Deriva a chave de pagamento + endereco preprod do mnemonico.

    Caminhos CIP-1852 padrao — mesmos usados por Eternl, Lace e
    outras carteiras Cardano. Endereco resultante coincide com o
    primeiro endereco da carteira (account 0, address 0).

    Analogia: a partir das 24 palavras (senha mestre), gera:
      - chave de pagamento = sua "assinatura digital" para autorizar txs
      - endereco = seu "numero de conta" na rede preprod
    """
    # Gera a carteira HD (Hierarchical Deterministic) a partir das
    # 24 palavras — todas as chaves derivam dessa raiz.
    hd = HDWallet.from_mnemonic(mnemonic)

    # Deriva a chave de pagamento via caminho CIP-1852.
    # "m/1852'/1815'/0'/0/0" e o padrao — mesmo que Eternl/Lace usam
    # para o primeiro endereco. Analogia: como abrir o "cofre 0"
    # dentro da carteira para pegar a chave de assinatura.
    payment = ExtendedSigningKey.from_hdwallet(
        hd.derive_from_path("m/1852'/1815'/0'/0/0")
    )

    # Deriva a chave de stake (necessaria para compor o endereco
    # completo, mesmo que nao estejamos delegando).
    stake = ExtendedSigningKey.from_hdwallet(
        hd.derive_from_path("m/1852'/1815'/0'/2/0")
    )

    # Monta o endereco preprod combinando as duas chaves.
    # Network.TESTNET = preprod (rede de testes).
    addr = Address(
        payment.to_verification_key().hash(),
        stake.to_verification_key().hash(),
        network=Network.TESTNET,
    )
    return payment, addr
