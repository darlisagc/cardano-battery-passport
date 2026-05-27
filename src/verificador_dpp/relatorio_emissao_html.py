"""Relatorio HTML de emissao — gerado automaticamente apos cada issuance.

Gera uma pagina HTML auto-contida (receipt) mostrando os dados da
credencial recem-emitida, com link clicavel ao Cexplorer preprod.

Usado por ambos os emissores (emissor_direto e emissor_sdk) para dar
feedback visual imediato ao participante do workshop.
"""

from __future__ import annotations

# -- Actor configuration -------------------------------------------------------

_ACTOR_CONFIG: dict[str, dict[str, str]] = {
    "origem": {
        "titulo": "Origem do Litio",
        "subtitulo": "Ator 1 — MineraLitio Jequitinhonha",
        "cor_header_from": "#1a237e",
        "cor_header_to": "#283593",
        "cor_card": "#2e7d32",
        "icon": (
            '<svg viewBox="0 0 24 24" class="card-icon" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round">'
            '<path d="M14.5 9.5L12 12"/>'
            '<path d="M4 20l6-6"/>'
            '<path d="M10.5 10.5L3 3"/>'
            '<path d="M21 3l-6.5 6.5"/>'
            '<path d="M16 3l5 5"/>'
            "</svg>"
        ),
    },
    "celula": {
        "titulo": "Fabricacao das Celulas",
        "subtitulo": "Ator 2 — CellTech Brasil",
        "cor_header_from": "#1a237e",
        "cor_header_to": "#283593",
        "cor_card": "#1565c0",
        "icon": (
            '<svg viewBox="0 0 24 24" class="card-icon" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round">'
            '<path d="M2 20h20"/>'
            '<path d="M5 20V8l5 4V8l5 4V4h4v16"/>'
            "</svg>"
        ),
    },
    "pack": {
        "titulo": "Montagem do Pack",
        "subtitulo": "Ator 3 — PackMontadora SP",
        "cor_header_from": "#1a237e",
        "cor_header_to": "#283593",
        "cor_card": "#f9a825",
        "icon": (
            '<svg viewBox="0 0 24 24" class="card-icon" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round">'
            '<rect x="2" y="7" width="20" height="14" rx="2"/>'
            '<path d="M12 7V3"/><path d="M2 11h20"/>'
            '<path d="M7 7V4"/><path d="M17 7V4"/>'
            "</svg>"
        ),
    },
    "reciclagem": {
        "titulo": "Reciclagem de Bateria",
        "subtitulo": "Ator 4 — RecicLar Sorocaba",
        "cor_header_from": "#004d40",
        "cor_header_to": "#00695c",
        "cor_card": "#00695c",
        "icon": (
            '<svg viewBox="0 0 24 24" class="card-icon" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round">'
            '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>'
            '<path d="M21 3v5h-5"/>'
            '<path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>'
            '<path d="M3 21v-5h5"/>'
            "</svg>"
        ),
    },
}

_ICON_BATTERY_HEADER = (
    '<svg viewBox="0 0 48 48" class="header-icon" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<rect x="4" y="14" width="36" height="20" rx="3"/>'
    '<path d="M44 22v4"/>'
    '<path d="M12 22v4"/><path d="M20 22v4"/><path d="M28 22v4"/>'
    "</svg>"
)


# -- Public API ----------------------------------------------------------------


class RelatorioEmissaoHTML:
    """Gera relatorio HTML de emissao (receipt) para uma credencial."""

    def gerar(
        self,
        ator: str,
        payload: dict,
        tx_hash: str,
        data_hash: str,
    ) -> str:
        """Gera o HTML auto-contido do receipt de emissao.

        Parametros:
            ator:      nome do ator (origem, celula, pack, reciclagem)
            payload:   dicionario com os campos do payload DPP
            tx_hash:   hash da transacao Cardano
            data_hash: sha256(gtin+serial) do produto

        Retorna:
            String HTML pronta para salvar como .html.
        """
        cfg = _ACTOR_CONFIG.get(ator, _ACTOR_CONFIG["origem"])

        # Build field rows
        campos_html = self._campos(payload)
        materiais_html = self._materiais(payload)
        referencias_html = self._referencias(payload)

        cexplorer_url = f"https://preprod.cexplorer.io/tx/{_esc(tx_hash)}"
        short_tx = tx_hash[:20] + "..." if len(tx_hash) > 20 else tx_hash
        short_dh = data_hash[:20] + "..." if len(data_hash) > 20 else data_hash

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Emissao DPP — {_esc(cfg['titulo'])}</title>
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
.header {{
    background: linear-gradient(135deg, {cfg['cor_header_from']}, {cfg['cor_header_to']});
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
.card {{
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    margin-bottom: 1.5rem;
    overflow: hidden;
    border-left: 6px solid {cfg['cor_card']};
}}
.card-header-strip {{
    height: 4px;
    width: 100%;
    background: {cfg['cor_card']};
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
.card-body {{
    padding: 0 1.2rem 1.2rem;
}}
.card-body dl {{
    display: grid;
    grid-template-columns: 180px 1fr;
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
.referencias {{
    margin-top: 0.8rem;
}}
.referencias h4 {{
    font-size: 0.9rem;
    font-weight: 600;
    color: #555;
    margin-bottom: 0.4rem;
}}
.ref-badges {{
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}}
.ref-badge {{
    display: inline-block;
    background: #e8eaf6;
    border: 1px solid #9fa8da;
    border-left: 3px solid #5c6bc0;
    border-radius: 6px;
    padding: 0.4rem 0.9rem;
    font-size: 0.82rem;
    color: #333;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}}
.ref-badge strong {{
    font-weight: 700;
    margin-right: 0.3rem;
}}
.ref-badge a {{
    color: #3949ab;
    text-decoration: none;
}}
.ref-badge a:hover {{
    text-decoration: underline;
}}
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
.hashes {{
    margin-top: 1rem;
    padding: 0.8rem 1rem;
    background: #fafafa;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 0.78rem;
    color: #666;
    word-break: break-all;
}}
.hashes strong {{
    color: #444;
}}
.hashes a {{
    color: #5c6bc0;
    text-decoration: none;
}}
.hashes a:hover {{
    text-decoration: underline;
}}
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
@media (max-width: 600px) {{
    .header h1 {{ font-size: 1.3rem; }}
    .card-body dl {{
        grid-template-columns: 1fr;
    }}
    .card-body dt {{
        margin-top: 0.3rem;
    }}
}}
</style>
</head>
<body>
<div class="header">
    {_ICON_BATTERY_HEADER}
    <span class="header-pretitle">Emissao DPP — Certificado Registrado</span>
    <h1>{_esc(cfg['titulo'])}</h1>
    <p>{_esc(cfg['subtitulo'])}</p>
</div>
<div class="container">
    <div class="card">
        <div class="card-header-strip"></div>
        <div class="card-header">{cfg['icon']}{_esc(cfg['titulo'])}</div>
        <div class="card-tx">Tx: <a href="{cexplorer_url}" target="_blank" rel="noopener noreferrer" title="{_esc(tx_hash)}">{_esc(short_tx)}</a></div>
        <div class="card-body">
            <dl>
{campos_html}
            </dl>
{materiais_html}{referencias_html}
        </div>
    </div>
    <div class="hashes">
        <strong>tx_hash:</strong> <a href="{cexplorer_url}" target="_blank" rel="noopener noreferrer">{_esc(tx_hash)}</a><br>
        <strong>data_hash:</strong> {_esc(data_hash)}
    </div>
    <div class="verified-banner">
        <div class="verified-badge">
            <svg viewBox="0 0 80 80"><circle cx="40" cy="40" r="38" fill="none" stroke="#43a047" stroke-width="2"/><circle cx="40" cy="40" r="32" fill="#43a047"/><polyline points="28 40 36 48 52 32" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div class="verified-pretitle">Emissao Registrada</div>
        <div class="verified-title">Emissao registrada na Blockchain Cardano</div>
        <div class="verified-subtitle">
            Este certificado DPP foi ancorado on-chain na rede Cardano preprod.
        </div>
        <div class="verified-chain">Rede: Cardano Preprod &bull; Template: Digital Product Passport</div>
    </div>
    <div class="footer">
        Certificado emitido e registrado on-chain.
        <div class="footer-protocol">Template DPP &bull; Rede Cardano Preprod</div>
    </div>
</div>
</body>
</html>"""

    def _campos(self, payload: dict) -> str:
        """Gera os <dt>/<dd> para campos padrao do payload."""
        field_map = [
            ("name", "Produto"),
            ("issuer", "Emitente"),
            ("gtin", "GTIN"),
            ("origin", "Origem"),
            ("manufactured", "Fabricado em"),
            ("carbon_footprint", "Pegada de carbono"),
            ("recycled_content", "Conteudo reciclado"),
        ]
        items = []
        for key, label in field_map:
            valor = payload.get(key)
            if valor is None:
                continue
            valor_str = str(valor).strip()
            if not valor_str:
                continue
            items.append(
                f"                <dt>{_esc(label)}</dt>"
                f"<dd>{_esc(valor_str)}</dd>"
            )
        return "\n".join(items)

    def _materiais(self, payload: dict) -> str:
        """Gera a secao de materiais (campos mat_*)."""
        mats = {
            k[len("mat_"):]: str(v)
            for k, v in payload.items()
            if k.startswith("mat_")
        }
        if not mats:
            return ""
        tags = "\n".join(
            f'                <span class="mat-tag">'
            f"{_esc(k)}: {_esc(v)}</span>"
            for k, v in mats.items()
        )
        return (
            '            <div class="materials">\n'
            "                <h4>Materiais</h4>\n"
            '                <div class="mat-tags">\n'
            f"{tags}\n"
            "                </div>\n"
            "            </div>\n"
        )

    def _referencias(self, payload: dict) -> str:
        """Gera a secao de referencias (campos cert_*_credential_tx)."""
        label_map = {
            "pack": "Pack",
            "celula": "Celula",
            "origem": "Origem",
        }
        refs = {
            k[len("cert_"):]: str(v)
            for k, v in payload.items()
            if k.startswith("cert_") and k.endswith("_credential_tx")
        }
        if not refs:
            return ""
        badges = []
        for chave, ref_tx in refs.items():
            nome = chave.replace("_credential_tx", "")
            label = label_map.get(nome, nome)
            short = ref_tx[:16] + "..." if len(ref_tx) > 16 else ref_tx
            url = f"https://preprod.cexplorer.io/tx/{_esc(ref_tx)}"
            badges.append(
                f'                <span class="ref-badge">'
                f"<strong>{_esc(label)}</strong>"
                f'<a href="{url}" target="_blank" '
                f'rel="noopener noreferrer" title="{_esc(ref_tx)}">'
                f"{_esc(short)}</a></span>"
            )
        badges_html = "\n".join(badges)
        return (
            '            <div class="referencias">\n'
            "                <h4>Referencias na Cadeia</h4>\n"
            '                <div class="ref-badges">\n'
            f"{badges_html}\n"
            "                </div>\n"
            "            </div>\n"
        )


def _esc(text: str) -> str:
    """Escapa caracteres HTML especiais."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
