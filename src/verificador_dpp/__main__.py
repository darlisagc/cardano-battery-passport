"""Help dispatcher para o pacote verificador_dpp.

Modulos do workshop:
    emissor_direto      Emite DPP direto via PyCardano (Opcao A)
    emissor_sdk         Emite DPP via uverify-sdk      (Opcao B)
    verificador_direto  Verifica via Blockfrost+parser (Opcao A)
    verificador_sdk     Verifica via uverify-sdk       (Opcao B)
"""

import sys

USO = """\
verificador_dpp - Workshop DPP Cardano

Para emitir credenciais (Secao 2):
  python -m verificador_dpp.emissor_direto --ator origem|celula|pack|reciclagem
  python -m verificador_dpp.emissor_sdk    --ator origem|celula|pack|reciclagem

Para verificar (Secao 3):
  python -m verificador_dpp.verificador_direto [tx_hash]
  python -m verificador_dpp.verificador_sdk    [--tx ... --hash ...]

Configuracao em .env (ver .env.example).
"""


def main() -> None:
    print(USO)
    sys.exit(0)


if __name__ == "__main__":
    main()
