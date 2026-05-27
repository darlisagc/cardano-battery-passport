"""Relatorio HTML do PassaporteBateria (Digital Product Passport).

Gera um relatorio HTML auto-contido (CSS inline, sem dependencias externas)
com layout moderno baseado em cards para exibicao no navegador.

Cada CredencialDPP aparece como um card com borda colorida:
  - Verde: Origem (litio)
  - Azul:  Celula (fabricacao)
  - Amarelo: Pack (montagem)
  - Teal:  Reciclagem (fim de vida) [opcional]
"""

from ._html_utils import cexplorer_link as _cexplorer_link
from ._html_utils import esc_html as _esc
from .modelos import CredencialDPP, PassaporteBateria

# -- Inline SVG icons (no external dependencies) -----------------------------

_ICON_BATTERY_HEADER = (
    '<svg viewBox="0 0 48 48" class="header-icon" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<rect x="4" y="14" width="36" height="20" rx="3"/>'
    '<path d="M44 22v4"/>'
    '<path d="M12 22v4"/><path d="M20 22v4"/><path d="M28 22v4"/>'
    "</svg>"
)

_ICON_PICKAXE = (
    '<svg viewBox="0 0 24 24" class="card-icon" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M14.5 9.5L12 12"/>'
    '<path d="M4 20l6-6"/>'
    '<path d="M10.5 10.5L3 3"/>'
    '<path d="M21 3l-6.5 6.5"/>'
    '<path d="M16 3l5 5"/>'
    "</svg>"
)

_ICON_FACTORY = (
    '<svg viewBox="0 0 24 24" class="card-icon" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M2 20h20"/>'
    '<path d="M5 20V8l5 4V8l5 4V4h4v16"/>'
    "</svg>"
)

_ICON_PACK = (
    '<svg viewBox="0 0 24 24" class="card-icon" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<rect x="2" y="7" width="20" height="14" rx="2"/>'
    '<path d="M12 7V3"/><path d="M2 11h20"/>'
    '<path d="M7 7V4"/><path d="M17 7V4"/>'
    "</svg>"
)

_ICON_RECYCLE = (
    '<svg viewBox="0 0 24 24" class="card-icon" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>'
    '<path d="M21 3v5h-5"/>'
    '<path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>'
    '<path d="M3 21v-5h5"/>'
    "</svg>"
)

_CARD_ICONS = {
    "origem": _ICON_PICKAXE,
    "celula": _ICON_FACTORY,
    "pack": _ICON_PACK,
    "reciclagem": _ICON_RECYCLE,
}

_ICON_CHAIN_LINK = (
    '<svg viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>'
    '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'
    "</svg>"
)

_ICON_SHIELD_CHECK = (
    '<svg viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'
    '<polyline points="9 12 11 14 15 10"/>'
    "</svg>"
)

_CHEVRON_SVG = (
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
    'stroke="#aaa" stroke-width="2.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<polyline points="9 6 15 12 9 18"/>'
    "</svg>"
)


class RelatorioHTML:
    """Gera relatorios HTML de passaportes de bateria.

    Uso:
        relatorio = RelatorioHTML()
        passaporte = PassaporteBateria(origem, celula, pack)
        html = relatorio.gerar(passaporte)
    """

    def gerar(self, passaporte: PassaporteBateria) -> str:
        """Gera o relatorio HTML completo do passaporte.

        Parametros:
            passaporte: objeto PassaporteBateria com as tres credenciais.

        Retorna:
            String HTML auto-contida pronta para salvar como .html.
        """
        cards = []
        cards.append(
            self._card("Origem (lítio)", passaporte.origem, "#2e7d32", "origem")
        )
        cards.append(
            self._card(
                "Fabricação das células", passaporte.celula, "#1565c0", "celula"
            )
        )
        cards.append(
            self._card("Montagem do pack", passaporte.pack, "#f9a825", "pack")
        )
        if passaporte.reciclagem is not None:
            cards.append(
                self._card(
                    "Reciclagem", passaporte.reciclagem, "#00695c", "reciclagem"
                )
            )

        cards_html = "\n".join(cards)

        # Build supply chain flow diagram (dynamic step count).
        flow_steps = [
            ("origem", "Origem"),
            ("celula", "C&eacute;lula"),
            ("pack", "Pack"),
        ]
        if passaporte.reciclagem is not None:
            flow_steps.append(("reciclagem", "Reciclagem"))

        flow_parts = []
        for i, (css_class, label) in enumerate(flow_steps):
            if i > 0:
                flow_parts.append(f'        <span class="flow-arrow">{_CHEVRON_SVG}</span>')
            flow_parts.append(
                f'        <div class="flow-step {css_class}">'
                f'<span class="step-number">{i + 1}</span>{label}</div>'
            )
        flow_html = "\n".join(flow_parts)

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Passaporte Digital de Produto — Bateria EV</title>
<style>
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, sans-serif;
    background: #f5f5f5;
    color: #333;
    line-height: 1.6;
}}

/* Header with geometric overlay */
.header {{
    background: linear-gradient(135deg, #1a237e, #283593);
    color: #fff;
    padding: 3rem 1rem 2.5rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}}
.header::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        45deg,
        transparent,
        transparent 10px,
        rgba(255,255,255,0.03) 10px,
        rgba(255,255,255,0.03) 20px
    );
    pointer-events: none;
}}
.header-icon {{
    width: 48px;
    height: 48px;
    margin-bottom: 0.5rem;
    opacity: 0.9;
    color: #fff;
}}
.header-pretitle {{
    display: block;
    font-size: 0.7rem;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    opacity: 0.7;
    margin-bottom: 0.6rem;
    font-weight: 500;
    position: relative;
}}
.header h1 {{
    font-size: 1.8rem;
    margin-bottom: 0.5rem;
    font-weight: 700;
    position: relative;
}}
.header p {{
    font-size: 1rem;
    opacity: 0.75;
    font-weight: 300;
    letter-spacing: 0.02em;
    position: relative;
}}
.container {{
    max-width: 860px;
    margin: 0 auto;
    padding: 1.5rem 1rem 2rem;
}}

/* Supply chain flow */
.flow {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin: 1.5rem 0 2rem;
    flex-wrap: wrap;
    position: relative;
}}
.flow-step {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.6rem 1.2rem;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.95rem;
    color: #fff;
    position: relative;
    z-index: 1;
}}
.flow-step.origem      {{ background: #2e7d32; }}
.flow-step.celula      {{ background: #1565c0; }}
.flow-step.pack        {{ background: #f9a825; color: #333; }}
.flow-step.reciclagem  {{ background: #00695c; }}
.step-number {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: rgba(255,255,255,0.25);
    font-size: 0.75rem;
    font-weight: 700;
    line-height: 1;
    flex-shrink: 0;
}}
.flow-step.pack .step-number {{
    background: rgba(0,0,0,0.12);
}}
.flow-arrow {{
    display: inline-flex;
    align-items: center;
    margin: 0 0.3rem;
    color: #999;
}}

/* Credential cards */
.card {{
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    margin-bottom: 1.5rem;
    overflow: hidden;
}}
.card-border {{
    border-left: 6px solid;
}}
.card-header-strip {{
    height: 4px;
    width: 100%;
}}
.card-header {{
    padding: 1rem 1.2rem 0.6rem;
    font-size: 1.15rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    position: relative;
}}
.card-icon {{
    width: 22px;
    height: 22px;
    flex-shrink: 0;
    color: #555;
}}
.card-body {{
    padding: 0 1.2rem 1.2rem;
}}
.card-body dl {{
    display: grid;
    grid-template-columns: 160px 1fr;
    gap: 0;
}}
.card-body dt,
.card-body dd {{
    padding: 0.3rem 0.5rem;
    font-size: 0.9rem;
    margin: 0;
}}
.card-body dt {{
    font-weight: 600;
    color: #555;
}}
.card-body dt:nth-of-type(even),
.card-body dd:nth-of-type(even) {{
    background: rgba(0,0,0,0.025);
}}
.materials {{
    margin-top: 0.8rem;
}}
.materials h4 {{
    font-size: 0.9rem;
    font-weight: 600;
    color: #555;
    margin-bottom: 0.4rem;
}}
.mat-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
}}
.mat-tag {{
    background: #e8eaf6;
    padding: 0.3rem 0.8rem 0.3rem 0.6rem;
    border-radius: 20px;
    font-size: 0.82rem;
    color: #333;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07);
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
}}
.mat-tag::before {{
    content: "";
    display: inline-block;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #5c6bc0;
    flex-shrink: 0;
}}
.card-tx {{
    padding: 0.2rem 1.2rem 0.4rem;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 0.78rem;
    color: #888;
}}
.card-tx a {{
    color: #5c6bc0;
    text-decoration: none;
}}
.card-tx a:hover {{
    text-decoration: underline;
    color: #3949ab;
}}
.card-absent {{
    padding: 1.2rem;
    color: #888;
    font-style: italic;
}}

/* Emission method badge */
.emission-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.6rem;
    border-radius: 12px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    border: 1px solid;
    position: absolute;
    top: 8px;
    right: 12px;
}}
.emission-badge svg {{
    width: 12px;
    height: 12px;
    flex-shrink: 0;
}}
.emission-badge.metadata {{
    color: #666;
    border-color: #ccc;
    background: #f5f5f5;
}}
.emission-badge.uverify {{
    color: #1565c0;
    border-color: #90caf9;
    background: #e3f2fd;
}}

/* Verified banner */
.verified-banner {{
    background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
    border: 2px solid #43a047;
    border-radius: 12px;
    padding: 1.5rem 1.2rem;
    margin: 2rem 0 1rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}}
.verified-banner::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        45deg,
        transparent,
        transparent 10px,
        rgba(46,125,50,0.03) 10px,
        rgba(46,125,50,0.03) 20px
    );
    pointer-events: none;
}}
.verified-badge {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 64px;
    height: 64px;
    margin-bottom: 0.8rem;
    position: relative;
}}
.verified-badge svg {{
    width: 64px;
    height: 64px;
}}
.verified-pretitle {{
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #388e3c;
    font-weight: 600;
    margin-bottom: 0.3rem;
    position: relative;
}}
.verified-title {{
    font-size: 1.25rem;
    font-weight: 700;
    color: #2e7d32;
    margin-bottom: 0.3rem;
    position: relative;
}}
.verified-subtitle {{
    font-size: 0.92rem;
    color: #555;
    margin-bottom: 0.6rem;
    position: relative;
}}
.verified-chain {{
    display: inline-block;
    background: #fff;
    border: 1px solid #a5d6a7;
    border-radius: 6px;
    padding: 0.4rem 1rem;
    font-size: 0.82rem;
    color: #666;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    position: relative;
}}

/* Footer */
.footer {{
    text-align: center;
    padding: 1.5rem 1rem;
    color: #777;
    font-size: 0.85rem;
    border-top: 1px solid #e0e0e0;
    margin-top: 1rem;
}}
.footer-protocol {{
    font-size: 0.78rem;
    color: #999;
    margin-top: 0.3rem;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
}}

/* Responsive */
@media (max-width: 600px) {{
    .header h1 {{ font-size: 1.3rem; }}
    .card-body dl {{
        grid-template-columns: 1fr;
    }}
    .card-body dt {{
        margin-top: 0.3rem;
    }}
    .flow {{
        flex-direction: column;
    }}
    .flow-arrow {{
        transform: rotate(90deg);
    }}
}}
</style>
</head>
<body>
<div class="header">
    {_ICON_BATTERY_HEADER}
    <span class="header-pretitle">Certificado Digital</span>
    <h1>Passaporte Digital de Produto &mdash; Bateria EV</h1>
    <p>Workshop Cardano &mdash; De Jequitinhonha a Europa</p>
</div>
<div class="container">
    <div class="flow">
{flow_html}
    </div>
{cards_html}
    <div class="verified-banner">
        <div class="verified-badge">
            <svg viewBox="0 0 80 80"><circle cx="40" cy="40" r="38" fill="none" stroke="#43a047" stroke-width="2"/><circle cx="40" cy="40" r="32" fill="#43a047"/><polyline points="28 40 36 48 52 32" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div class="verified-pretitle">Certificado Verificado</div>
        <div class="verified-title">Verificado na Blockchain Cardano</div>
        <div class="verified-subtitle">
            Todas as credenciais desta cadeia de suprimentos foram ancoradas
            e verificadas on-chain na rede Cardano preprod.
        </div>
        <div class="verified-chain">Rede: Cardano Preprod &bull; Template: Digital Product Passport</div>
    </div>
    <div class="footer">
        Cadeia de rastreabilidade verificada on-chain.
        <div class="footer-protocol">Template DPP &bull; Rede Cardano Preprod</div>
    </div>
</div>
</body>
</html>"""

    @staticmethod
    def _emission_badge(metodo: str | None) -> str:
        """Gera o HTML do badge de metodo de emissao."""
        if metodo == "metadata":
            return (
                f'<span class="emission-badge metadata">'
                f"{_ICON_CHAIN_LINK}Metadata</span>"
            )
        if metodo == "uverify":
            return (
                f'<span class="emission-badge uverify">'
                f"{_ICON_SHIELD_CHECK}UVerify</span>"
            )
        return ""

    def _card(
        self, titulo: str, c: CredencialDPP | None, cor: str, tipo: str = ""
    ) -> str:
        """Gera o HTML de um card de credencial.

        Parametros:
            titulo: titulo da secao (ex: "Origem (lítio)").
            c:      credencial DPP, ou None se ausente.
            cor:    cor CSS da borda esquerda do card.
            tipo:   tipo do card para selecao de icone.
        """
        icon_html = _CARD_ICONS.get(tipo, "")

        if c is None:
            return (
                f'    <div class="card card-border" style="border-left-color:{cor}">\n'
                f'        <div class="card-header-strip" style="background:{cor}"></div>\n'
                f'        <div class="card-header">{icon_html}{_esc(titulo)}</div>\n'
                f'        <div class="card-absent">'
                f"(credencial ausente ou nao encontrada na cadeia)"
                f"</div>\n"
                f"    </div>"
            )

        badge_html = self._emission_badge(c.metodo_emissao)

        tx_link_html = ""
        if c.tx_hash:
            tx_link_html = (
                f'        <div class="card-tx">'
                f"Tx: {_cexplorer_link(c.tx_hash)}</div>\n"
            )

        campos = [
            ("Emitente", c.emitente),
            ("Produto", c.nome),
            ("GTIN", c.gtin),
            ("Origem", c.origem),
            ("Fabricado em", c.fabricado_em),
            ("Pegada de carbono", c.pegada_carbono),
            ("Conteúdo reciclado", c.conteudo_reciclado),
        ]

        dl_items = []
        for rotulo, valor in campos:
            if valor is None:
                continue
            valor_str = str(valor).strip()
            if not valor_str:
                continue
            dl_items.append(
                f"            <dt>{_esc(rotulo)}</dt>"
                f"<dd>{_esc(valor_str)}</dd>"
            )

        dl_html = "\n".join(dl_items)

        materiais_html = ""
        if c.materiais:
            tags = "\n".join(
                f'                <span class="mat-tag">'
                f"{_esc(k)}: {_esc(v)}</span>"
                for k, v in c.materiais.items()
            )
            materiais_html = (
                f'        <div class="materials">\n'
                f"            <h4>Materiais</h4>\n"
                f'            <div class="mat-tags">\n'
                f"{tags}\n"
                f"            </div>\n"
                f"        </div>\n"
            )

        return (
            f'    <div class="card card-border" style="border-left-color:{cor}">\n'
            f'        <div class="card-header-strip" style="background:{cor}"></div>\n'
            f'        <div class="card-header">{icon_html}{_esc(titulo)}{badge_html}</div>\n'
            f"{tx_link_html}"
            f'        <div class="card-body">\n'
            f"            <dl>\n"
            f"{dl_html}\n"
            f"            </dl>\n"
            f"{materiais_html}"
            f"        </div>\n"
            f"    </div>"
        )


