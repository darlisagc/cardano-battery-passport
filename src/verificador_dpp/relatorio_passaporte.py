"""Monta o relatorio em portugues a partir da cadeia de credenciais."""

from .modelos import CredencialDPP, PassaporteBateria


class RelatorioPassaporte:
    def gerar(self, passaporte: PassaporteBateria) -> str:
        linhas: list[str] = []
        linhas.append("=" * 64)
        linhas.append("  PASSAPORTE VALIDO")
        linhas.append("=" * 64)
        linhas.append("")

        self._secao(linhas, "Origem (lítio)", passaporte.origem)
        self._secao(linhas, "Fabricação das células", passaporte.celula)
        self._secao(linhas, "Montagem do pack", passaporte.pack)

        linhas.append("")
        linhas.append("Cadeia de rastreabilidade verificada on-chain.")
        linhas.append("Todas as credenciais foram ancoradas em Cardano preprod.")
        return "\n".join(linhas)

    def _secao(
        self, linhas: list[str], titulo: str, c: CredencialDPP | None
    ) -> None:
        linhas.append(f"-- {titulo} --")
        if c is None:
            linhas.append("  (credencial ausente ou nao encontrada na cadeia)")
            linhas.append("")
            return

        self._linha(linhas, "Emitente", c.emitente)
        self._linha(linhas, "Produto", c.nome)
        self._linha(linhas, "GTIN", c.gtin)
        self._linha(linhas, "Origem", c.origem)
        self._linha(linhas, "Fabricado em", c.fabricado_em)
        self._linha(linhas, "Pegada de carbono", c.pegada_carbono)
        self._linha(linhas, "Conteúdo reciclado", c.conteudo_reciclado)

        if c.materiais:
            linhas.append("  Materiais:")
            for k, v in c.materiais.items():
                linhas.append(f"    - {k}: {v}")
        linhas.append("")

    @staticmethod
    def _linha(linhas: list[str], rotulo: str, valor: str | None) -> None:
        if valor is None or not valor.strip():
            return
        linhas.append(f"  {rotulo}: {valor}")
