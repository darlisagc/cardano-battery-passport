"""Utilidades HTML compartilhadas pelos modulos de relatorio.

Funções de escape HTML e geração de links Cexplorer usadas por:
  - relatorio_html.py
  - relatorio_emissao_html.py
  - relatorio_reciclagem_html.py
"""


def esc_html(text: str) -> str:
    """Escapa caracteres HTML especiais."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def cexplorer_link(tx_hash: str) -> str:
    """Gera um link HTML clicavel para o Cexplorer preprod."""
    short = tx_hash[:16] + "..." if len(tx_hash) > 16 else tx_hash
    url = f"https://preprod.cexplorer.io/tx/{esc_html(tx_hash)}"
    return (
        f'<a href="{url}" target="_blank" '
        f'rel="noopener noreferrer" title="{esc_html(tx_hash)}">'
        f"{esc_html(short)}</a>"
    )
