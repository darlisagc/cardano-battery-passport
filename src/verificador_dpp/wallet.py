"""Carteira HD compartilhada (CIP-1852).

Usada pelos dois emissores (direto via PyCardano e via uverify-sdk).
"""

from __future__ import annotations

from pycardano import Address, ExtendedSigningKey, HDWallet, Network


def carregar_carteira(mnemonic: str) -> tuple[ExtendedSigningKey, Address]:
    """Deriva a chave de pagamento + endereco preprod do mnemonico.

    Caminhos CIP-1852 padrao - mesmos usados por Eternl, Lace e
    outras carteiras Cardano. Endereco resultante coincide com o
    primeiro endereco da carteira (account 0, address 0).
    """
    hd = HDWallet.from_mnemonic(mnemonic)
    payment = ExtendedSigningKey.from_hdwallet(
        hd.derive_from_path("m/1852'/1815'/0'/0/0")
    )
    stake = ExtendedSigningKey.from_hdwallet(
        hd.derive_from_path("m/1852'/1815'/0'/2/0")
    )
    addr = Address(
        payment.to_verification_key().hash(),
        stake.to_verification_key().hash(),
        network=Network.TESTNET,
    )
    return payment, addr
