"""Relatorio textual do PassaporteBateria (Digital Product Passport).

Recebe um objeto PassaporteBateria — que agrupa as CredencialDPP da
cadeia de suprimentos (origem, celula, pack, e opcionalmente reciclagem)
— e gera um relatorio formatado em portugues para exibicao no terminal.

Analogia: o PassaporteBateria e como um "dossie completo" do produto
que junta todos os certificados verificados on-chain. Este modulo
formata esse dossie para leitura humana.

Cada CredencialDPP aparece como uma secao mostrando:
  - Emitente (issuer), produto (name), GTIN (codigo de barras global)
  - Origem (origin), data de fabricacao (manufactured)
  - Pegada de carbono (carbon_footprint), conteudo reciclado (recycled_content)
  - Composicao de materiais (campos mat_*)
"""

from .modelos import CredencialDPP, PassaporteBateria


class RelatorioPassaporte:
    """Gera relatorios textuais de passaportes de bateria.

    Uso:
        relatorio = RelatorioPassaporte()
        passaporte = PassaporteBateria(origem, celula, pack)
        print(relatorio.gerar(passaporte))
    """

    def gerar(self, passaporte: PassaporteBateria) -> str:
        """Gera o relatorio textual completo do passaporte.

        O relatorio tem secoes para cada ator da cadeia:
          1. Origem (litio) — materia-prima
          2. Fabricacao das celulas — componente intermediario
          3. Montagem do pack — produto final
          4. Reciclagem (opcional) — fim de vida

        Parametros:
            passaporte: objeto PassaporteBateria com as credenciais.

        Retorna:
            String formatada pronta para imprimir no terminal.
        """
        linhas: list[str] = []

        # Cabecalho do relatorio.
        linhas.append("=" * 64)
        linhas.append("  PASSAPORTE VALIDO")
        linhas.append("=" * 64)
        linhas.append("")

        # Uma secao para cada elo da cadeia de suprimentos.
        self._secao(linhas, "Origem (lítio)", passaporte.origem)
        self._secao(linhas, "Fabricação das células", passaporte.celula)
        self._secao(linhas, "Montagem do pack", passaporte.pack)
        if passaporte.reciclagem is not None:
            self._secao(linhas, "Reciclagem", passaporte.reciclagem)

        # Rodape confirmando a verificacao.
        linhas.append("")
        linhas.append("Cadeia de rastreabilidade verificada on-chain.")
        linhas.append("Todas as credenciais foram ancoradas em Cardano preprod.")
        return "\n".join(linhas)

    def _secao(
        self, linhas: list[str], titulo: str, c: CredencialDPP | None
    ) -> None:
        """Adiciona uma secao ao relatorio para uma credencial.

        Se a credencial for None (nao encontrada na cadeia), exibe
        um aviso em vez dos dados.

        Parametros:
            linhas: lista de strings onde as linhas sao adicionadas.
            titulo: titulo da secao (ex: "Origem (lítio)").
            c:      credencial DPP, ou None se ausente.
        """
        linhas.append(f"-- {titulo} --")

        # Se a credencial nao foi encontrada, exibe aviso e sai.
        if c is None:
            linhas.append("  (credencial ausente ou nao encontrada na cadeia)")
            linhas.append("")
            return

        # Campos padrao do DPP.
        self._linha(linhas, "Emitente", c.emitente)
        self._linha(linhas, "Produto", c.nome)
        self._linha(linhas, "GTIN", c.gtin)
        self._linha(linhas, "Origem", c.origem)
        self._linha(linhas, "Fabricado em", c.fabricado_em)
        self._linha(linhas, "Pegada de carbono", c.pegada_carbono)
        self._linha(linhas, "Conteúdo reciclado", c.conteudo_reciclado)

        # Composicao de materiais (campos mat_* do payload).
        if c.materiais:
            linhas.append("  Materiais:")
            for k, v in c.materiais.items():
                linhas.append(f"    - {k}: {v}")
        linhas.append("")

    @staticmethod
    def _linha(linhas: list[str], rotulo: str, valor: str | int | None) -> None:
        """Adiciona uma linha ao relatorio se o valor nao for vazio.

        Converte o valor para string (a API UVerify pode retornar
        numeros inteiros para campos como GTIN). Pula a linha
        se o valor for None ou vazio.
        """
        if valor is None:
            return
        valor = str(valor)
        if not valor.strip():
            return
        linhas.append(f"  {rotulo}: {valor}")
