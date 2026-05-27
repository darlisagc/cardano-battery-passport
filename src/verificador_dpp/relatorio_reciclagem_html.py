"""Relatorio HTML de reciclagem (fim de vida) de bateria EV.

Gera um relatorio HTML auto-contido (CSS inline, sem dependencias externas)
para o certificado de reciclagem emitido pelo Ator 4 (RecicLar).

Este relatorio e independente do relatorio de cadeia de suprimentos
(relatorio_html.py). Exibe uma unica CredencialDPP com identidade
visual propria (teal) e secoes especificas para materiais recuperados
e rastreabilidade reversa (referencias aos 3 atores anteriores).
"""

from ._html_utils import cexplorer_link as _cexplorer_link
from ._html_utils import esc_html as _esc
from .modelos import CredencialDPP

# -- Inline SVG icons (no external dependencies) -----------------------------

_ICON_RECYCLE_HEADER = (
    '<svg viewBox="0 0 48 48" class="header-icon" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M6 24a18 18 0 0 1 18-18 18.75 18.75 0 0 1 13.48 5.48L42 16"/>'
    '<path d="M42 6v10h-10"/>'
    '<path d="M42 24a18 18 0 0 1-18 18 18.75 18.75 0 0 1-13.48-5.48L6 32"/>'
    '<path d="M6 42v-10h10"/>'
    "</svg>"
)

_ICON_RECYCLE_CARD = (
    '<svg viewBox="0 0 24 24" class="card-icon" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>'
    '<path d="M21 3v5h-5"/>'
    '<path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>'
    '<path d="M3 21v-5h5"/>'
    "</svg>"
)

_ICON_CHAIN = (
    '<svg viewBox="0 0 24 24" class="section-icon" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>'
    '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'
    "</svg>"
)

_CHEVRON_SVG = (
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
    'stroke="#aaa" stroke-width="2.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<polyline points="9 6 15 12 9 18"/>'
    "</svg>"
)


class RelatorioReciclagemHTML:
    """Gera relatorio HTML do certificado de reciclagem.

    Uso:
        relatorio = RelatorioReciclagemHTML()
        html = relatorio.gerar(credencial_reciclagem)
    """

    def gerar(self, reciclagem: CredencialDPP | None) -> str:
        """Gera o relatorio HTML completo de reciclagem.

        Parametros:
            reciclagem: credencial DPP de reciclagem, ou None se ausente.

        Retorna:
            String HTML auto-contida pronta para salvar como .html.
        """
        corpo = self._corpo(reciclagem)

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Certificado de Fim de Vida &mdash; Reciclagem de Bateria EV</title>
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
    background: linear-gradient(135deg, #004d40, #00695c);
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

/* Lifecycle flow */
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
.flow-step.pack        {{ background: #f9a825; color: #333; }}
.flow-step.desmontagem {{ background: #00897b; }}
.flow-step.reciclagem  {{ background: #004d40; }}
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

/* Credential card */
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

/* Materials */
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
    background: #e0f2f1;
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
    background: #00897b;
    flex-shrink: 0;
}}

/* Reverse traceability */
.rastreabilidade {{
    margin-top: 1rem;
}}
.rastreabilidade h4 {{
    font-size: 0.9rem;
    font-weight: 600;
    color: #555;
    margin-bottom: 0.4rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}}
.section-icon {{
    width: 18px;
    height: 18px;
    flex-shrink: 0;
    color: #00897b;
}}
.ref-badges {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}}
.ref-badge {{
    display: inline-block;
    background: #e0f2f1;
    border: 1px solid #80cbc4;
    border-left: 3px solid #00897b;
    border-radius: 6px;
    padding: 0.4rem 0.9rem;
    font-size: 0.82rem;
    color: #004d40;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}
.ref-badge strong {{
    font-weight: 700;
    margin-right: 0.3rem;
}}
.ref-badge a {{
    color: #004d40;
    text-decoration: none;
}}
.ref-badge a:hover {{
    text-decoration: underline;
    color: #00897b;
}}
.card-tx {{
    padding: 0.2rem 1.2rem 0.4rem;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 0.78rem;
    color: #888;
}}
.card-tx a {{
    color: #00897b;
    text-decoration: none;
}}
.card-tx a:hover {{
    text-decoration: underline;
    color: #004d40;
}}

.card-absent {{
    padding: 1.2rem;
    color: #888;
    font-style: italic;
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
    {_ICON_RECYCLE_HEADER}
    <span class="header-pretitle">Certificado Digital</span>
    <h1>Certificado de Fim de Vida &mdash; Reciclagem de Bateria EV</h1>
    <p>Workshop Cardano &mdash; De Jequitinhonha a Europa</p>
</div>
<div class="container">
    <div class="flow">
        <div class="flow-step pack"><span class="step-number">1</span>Pack</div>
        <span class="flow-arrow">{_CHEVRON_SVG}</span>
        <div class="flow-step desmontagem"><span class="step-number">2</span>Desmontagem</div>
        <span class="flow-arrow">{_CHEVRON_SVG}</span>
        <div class="flow-step reciclagem"><span class="step-number">3</span>Reciclagem</div>
    </div>
{corpo}
    <div class="footer">
        Certificado de reciclagem verificado on-chain &mdash; cadeia reversa completa.
        <div class="footer-protocol">Template DPP &bull; Rede Cardano Preprod</div>
    </div>
</div>
</body>
</html>"""

    def _corpo(self, c: CredencialDPP | None) -> str:
        """Gera o conteudo principal (card + banner)."""
        if c is None:
            return (
                '    <div class="card card-border" style="border-left-color:#00695c">\n'
                '        <div class="card-header-strip" style="background:#00695c"></div>\n'
                f'        <div class="card-header">{_ICON_RECYCLE_CARD}Reciclagem</div>\n'
                '        <div class="card-absent">'
                "(credencial ausente ou nao encontrada na cadeia)"
                "</div>\n"
                "    </div>"
            )

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
            ("Local", c.origem),
            ("Data de processamento", c.fabricado_em),
            ("Pegada de carbono", c.pegada_carbono),
            ("Conte\u00fado reciclado", c.conteudo_reciclado),
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

        # Materiais recuperados
        materiais_html = ""
        if c.materiais:
            tags = "\n".join(
                f'                <span class="mat-tag">'
                f"{_esc(k)}: {_esc(v)}</span>"
                for k, v in c.materiais.items()
            )
            materiais_html = (
                '        <div class="materials">\n'
                "            <h4>Materiais Recuperados</h4>\n"
                '            <div class="mat-tags">\n'
                f"{tags}\n"
                "            </div>\n"
                "        </div>\n"
            )

        # Rastreabilidade reversa
        rastreabilidade_html = ""
        if c.referencias:
            # Map reference keys to readable labels
            label_map = {
                "pack": "Pack",
                "celula": "C\u00e9lula",
                "origem": "Origem",
            }
            badges = []
            for chave, ref_tx_hash in c.referencias.items():
                # chave format: "pack_tx" → extract "pack"
                nome = chave.replace("_tx", "")
                label = label_map.get(nome, nome)
                short_hash = ref_tx_hash[:16] + "..." if len(ref_tx_hash) > 16 else ref_tx_hash
                hash_html = _cexplorer_link(ref_tx_hash)
                badges.append(
                    f'                <span class="ref-badge">'
                    f"<strong>{_esc(label)}</strong>{hash_html}</span>"
                )
            badges_html = "\n".join(badges)
            rastreabilidade_html = (
                '        <div class="rastreabilidade">\n'
                f"            <h4>{_ICON_CHAIN}Rastreabilidade Reversa</h4>\n"
                '            <div class="ref-badges">\n'
                f"{badges_html}\n"
                "            </div>\n"
                "        </div>\n"
            )

        card = (
            '    <div class="card card-border" style="border-left-color:#00695c">\n'
            '        <div class="card-header-strip" style="background:#00695c"></div>\n'
            f'        <div class="card-header">{_ICON_RECYCLE_CARD}Reciclagem de Bateria EV</div>\n'
            f"{tx_link_html}"
            '        <div class="card-body">\n'
            "            <dl>\n"
            f"{dl_html}\n"
            "            </dl>\n"
            f"{materiais_html}"
            f"{rastreabilidade_html}"
            "        </div>\n"
            "    </div>"
        )

        banner = (
            '    <div class="verified-banner">\n'
            '        <div class="verified-badge">\n'
            '            <svg viewBox="0 0 80 80"><circle cx="40" cy="40" r="38" fill="none" stroke="#43a047" stroke-width="2"/><circle cx="40" cy="40" r="32" fill="#43a047"/><polyline points="28 40 36 48 52 32" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></svg>\n'
            "        </div>\n"
            '        <div class="verified-pretitle">Certificado Verificado</div>\n'
            '        <div class="verified-title">Certificado de reciclagem verificado na Blockchain Cardano</div>\n'
            '        <div class="verified-subtitle">\n'
            "            Cadeia reversa completa: este certificado de reciclagem\n"
            "            referencia todas as etapas anteriores da cadeia de suprimentos.\n"
            "        </div>\n"
            '        <div class="verified-chain">Rede: Cardano Preprod &bull; Template: Digital Product Passport</div>\n'
            "    </div>"
        )

        return f"{card}\n{banner}"


