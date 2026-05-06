"""Help dispatcher para o pacote verificador_dpp.

Modulos do workshop:
    emissor_direto      Emite DPP direto via PyCardano (Opcao A)
    emissor_sdk         Emite DPP via uverify-sdk      (Opcao B)
    verificador_direto  Verifica via Blockfrost+parser (so Opcao A)
    verificador_sdk     Verifica via uverify-sdk       (so Opcao B/C)
    verificador_misto   Verifica cadeias heterogeneas  (A + B/C)
"""

import sys

USO = """\
verificador_dpp - Workshop DPP Cardano

Para emitir credenciais (Secao 2):
  python -m verificador_dpp.emissor_direto --ator origem|celula|pack|reciclagem
  python -m verificador_dpp.emissor_sdk    --ator origem|celula|pack|reciclagem
  (Opcao C: emita pela UI em https://app.preprod.uverify.io)

Para verificar (Secao 3):
  python -m verificador_dpp.verificador_direto [tx_hash]   # so Opcao A
  python -m verificador_dpp.verificador_sdk    [--tx ... --hash ...]  # so B/C
  python -m verificador_dpp.verificador_misto  [tx_hash]   # qualquer mistura

Configuracao em .env (ver .env.example).
"""


def main() -> None:
    print(USO)
    sys.exit(0)


if __name__ == "__main__":
    main()
