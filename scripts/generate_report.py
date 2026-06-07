#!/usr/bin/env python3
"""Build a single self-contained HTML report from every analysis script's compute().

One tab per analysis (Overview, Correlação, Per Capita, Dívida/Receita,
Tendências, Finalidades e Credores, Taxas de Aprovação, Pandemia), styled as a
printed-document card — gradient header, compact badges, CSS-only tabs, inline
SVG charts — mirroring the fp-control-html report style. No external deps: open
the resulting file directly, or run serve_report.py to view it over localhost.

Usage: python3 generate_report.py [output.html]
"""

import sys
from pathlib import Path

import approval_rates
import correlate
import debt_to_revenue
import pandemic_spotlight
import per_capita
import purposes_and_creditors
import trends
from _report_html import badge, esc, fmt_money, panel, render_page, svg_bar_chart, table

DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "report.html"


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

def build_overview(corr, purposes):
    years = corr["years"]
    pooled = corr["pooled"]["value"]
    body = f"""
    <h2>Crédito estadual e transferências constitucionais no Brasil</h2>
    <p class="note">
      Este relatório cruza dois conjuntos de dados públicos: as operações de crédito
      registradas no SADIPEM (Tesouro Nacional) e as transferências constitucionais
      recebidas pelos estados (FPE, FPM, FUNDEB, ICMS, IPVA, ITR, CIDE-Combustíveis…),
      cobrindo {esc(years[0])}-{esc(years[-1])}. Cada aba a seguir explora um ângulo
      diferente da relação entre os dois — correlação, peso per capita, exposição
      relativa à receita, evolução no tempo, finalidades/credores, seletividade do
      processo de aprovação e o efeito extraordinário da pandemia.
    </p>
    <div class="metric-grid">
      <div class="metric-card">
        <div class="label">Janela analisada</div>
        <div class="value">{esc(years[0])}–{esc(years[-1])}</div>
        <div class="extra">{len(years)} anos de dados locais</div>
      </div>
      <div class="metric-card">
        <div class="label">Correlação agregada (valor × transferências)</div>
        <div class="value">ρ = {pooled['spearman']:.3f}</div>
        <div class="extra">Spearman (robusta a outliers) · Pearson r = {pooled['pearson']:.3f}</div>
      </div>
      <div class="metric-card">
        <div class="label">Operações de crédito aprovadas</div>
        <div class="value">{fmt_money(purposes['total_value'])}</div>
        <div class="extra">{purposes['total_count']:,} operações ("Deferido*")</div>
      </div>
    </div>
    <p class="note">
      Use as abas acima para navegar entre as análises. O botão 🌙 alterna entre
      modo claro e escuro, e 🖨 gera uma versão para impressão (uma análise por página).
    </p>
    """
    return body


# ---------------------------------------------------------------------------
# Correlação
# ---------------------------------------------------------------------------

def build_correlate(result):
    years = result["years"]
    pooled = result["pooled"]
    by_year = result["by_year"]

    chart = svg_bar_chart(
        by_year, label_key="year", value_key="spearman_value",
        value_fmt=lambda v: f"ρ = {v:+.3f}", label_width=70, zero_centered=True,
    )
    cols = [
        ("Ano", "year", None),
        ("Pares (UF, ano)", "pairs", None),
        ("Pearson (valor)", lambda r: r["pearson_value"], lambda v: f"{v:.4f}"),
        ("Spearman (valor)", lambda r: r["spearman_value"], lambda v: f"{v:.4f}"),
        ("Pearson (qtd.)", lambda r: r["pearson_count"], lambda v: f"{v:.4f}"),
        ("Spearman (qtd.)", lambda r: r["spearman_count"], lambda v: f"{v:.4f}"),
    ]
    return f"""
    <h2>Correlação — crédito SADIPEM × transferências constitucionais</h2>
    <p class="note">
      Para cada par (estado, ano) presente nos dois conjuntos de dados, soma-se o
      valor (e a quantidade) das operações aprovadas no SADIPEM e o total recebido
      em transferências, e correlaciona-se as duas séries. Pearson mede a relação
      linear entre os valores brutos; Spearman correlaciona os <em>postos</em>
      (ranks), o que reduz drasticamente o efeito de outliers extremos — como a
      renegociação de ~R$ 224 bilhões de São Paulo em 2017, que por si só é maior
      que a soma de dezenas de outros pares.
    </p>
    <div class="metric-grid">
      <div class="metric-card">
        <div class="label">Agregado · valor × transferências</div>
        <div class="value">ρ = {pooled['value']['spearman']:.4f}</div>
        <div class="extra">Pearson r = {pooled['value']['pearson']:.4f} (sensível a outliers)</div>
      </div>
      <div class="metric-card">
        <div class="label">Agregado · quantidade × transferências</div>
        <div class="value">ρ = {pooled['count']['spearman']:.4f}</div>
        <div class="extra">Pearson r = {pooled['count']['pearson']:.4f}</div>
      </div>
    </div>
    <h3>Correlação Spearman (valor) por ano</h3>
    <p class="note">Dentro de um único ano todos os pares têm escala parecida, então Pearson e Spearman tendem a concordar mais — diferente do agregado pooled acima.</p>
    {chart}
    {table(cols, by_year)}
    """


# ---------------------------------------------------------------------------
# Per capita
# ---------------------------------------------------------------------------

def build_per_capita(result):
    def section(title, note, rows, unit_label):
        chart = svg_bar_chart(
            rows, label_key="uf", value_key="per_capita",
            value_fmt=lambda v: f"R$ {v:,.0f}",
            highlight=lambda r: abs(r["shift"]) >= per_capita.RANK_SHIFT_THRESHOLD,
            label_width=50,
        )
        cols = [
            ("UF", "uf", None),
            ("Per capita", lambda r: r["per_capita"], lambda v: f"R$ {v:,.2f}"),
            ("Total bruto", lambda r: r["raw_total"], fmt_money),
            ("População", lambda r: r["population"], lambda v: f"{v:,d}"),
            ("Posto bruto", "raw_rank", None),
            ("Posto per capita", "per_capita_rank", None),
            ("Variação", lambda r: r["shift"], lambda v: (
                "▲▲ acima do peso bruto" if v >= per_capita.RANK_SHIFT_THRESHOLD else
                "▼▼ total bruto superestima" if v <= -per_capita.RANK_SHIFT_THRESHOLD else
                f"{v:+d}"
            )),
        ]
        row_class = lambda r: "flag-extraordinary" if abs(r["shift"]) >= per_capita.RANK_SHIFT_THRESHOLD else ""
        return f"<h3>{esc(title)}</h3><p class='note'>{note}</p>{chart}{table(cols, rows, row_class=row_class)}"

    return f"""
    <h2>Visão per capita — peso fiscal por residente</h2>
    <p class="note">
      Totais brutos sempre favorecem os estados mais populosos. Dividindo pelo
      total de habitantes (estimativas IBGE 2025), a comparação passa a ser
      "quanto por residente" — uma leitura bem diferente de quem realmente pesa
      mais no orçamento per capita. Estados com variação de posto ≥ {per_capita.RANK_SHIFT_THRESHOLD}
      posições estão destacados.
    </p>
    {section(
        "Transferências constitucionais recebidas per capita",
        "Soma de todo o período local, dividida pela população 2025.",
        result["transfers"], "R$",
    )}
    {section(
        "Crédito SADIPEM aprovado (\"Deferido*\") per capita",
        "Soma de todo o período local, dividida pela população 2025.",
        result["sadipem"], "R$",
    )}
    """


# ---------------------------------------------------------------------------
# Dívida / receita
# ---------------------------------------------------------------------------

def build_debt_to_revenue(result):
    by_uf_chart = svg_bar_chart(
        result["by_uf"], label_key="uf", value_key="avg_ratio",
        value_fmt=lambda v: f"{v:.3f}", label_width=50,
    )
    year_cols = [
        ("Ano", "year", None),
        ("Estados", "states", None),
        ("Média nacional", lambda r: r["national_avg"], lambda v: f"{v:.4f}"),
        ("Maior (UF: razão)", lambda r: r["highest"], lambda v: f"{v[0]}: {v[1]:.4f}"),
        ("Menor (UF: razão)", lambda r: r["lowest"], lambda v: f"{v[0]}: {v[1]:.4f}"),
    ]
    uf_cols = [
        ("UF", "uf", None),
        ("Razão média", lambda r: r["avg_ratio"], lambda v: f"{v:.4f}"),
    ]
    years = result["years"]
    return f"""
    <h2>Dívida em relação à receita — exposição fiscal relativa</h2>
    <p class="note">
      Razão = valor de crédito SADIPEM aprovado ÷ transferências constitucionais
      recebidas, por (estado, ano). Uma razão próxima de zero indica que o novo
      crédito do estado é pequeno frente à sua receita constitucional; acima de 1
      significa que o estado tomou, naquele ano, mais crédito novo aprovado do que
      recebeu em transferências — uma leitura de "exposição fiscal" mais direta
      que um coeficiente de correlação.
    </p>
    <h3>Razão nacional por ano ({esc(years[0])}-{esc(years[-1])})</h3>
    {table(year_cols, result["by_year"])}
    <h3>Razão média por estado, do maior para o menor</h3>
    {by_uf_chart}
    {table(uf_cols, result["by_uf"])}
    """


# ---------------------------------------------------------------------------
# Tendências
# ---------------------------------------------------------------------------

def build_trends(result):
    def section(title, note, rows, value_fmt):
        chart = svg_bar_chart(
            rows, label_key="year", value_key="value", value_fmt=value_fmt, label_width=60,
        )
        cols = [
            ("Ano", "year", None),
            ("Total", lambda r: r["value"], value_fmt),
            ("Variação A/A", lambda r: r, lambda r: (
                "← ano em curso, não comparável" if r["is_partial"] else
                "—" if r["change_pct"] is None else
                f"{r['change_pct']:+.1f}%" + ("  ← variação extraordinária" if r["is_extraordinary"] else "")
            )),
        ]
        row_class = lambda r: (
            "flag-extraordinary" if r["is_extraordinary"] else
            "flag-up" if (r["change_pct"] or 0) > 0 else
            "flag-down" if r["change_pct"] is not None and r["change_pct"] < 0 else ""
        )
        return f"<h3>{esc(title)}</h3><p class='note'>{note}</p>{chart}{table(cols, rows, row_class=row_class)}"

    return f"""
    <h2>Tendências — evolução ano a ano</h2>
    <p class="note">
      Mantém o eixo do tempo intacto: totais nacionais por ano para os dois
      conjuntos de dados, mais a variação percentual ano a ano — assim, oscilações
      ligadas a eleições, choques econômicos ou mudanças de política (como a
      pandemia de 2020-21 — veja a aba Pandemia) ficam visíveis diretamente, em
      vez de suavizadas dentro de uma estatística agregada. Cada série cobre sua
      própria janela local (SADIPEM tem histórico completo desde 2002; transferências,
      uma janela rolante desde 2016), e variações acima de
      {trends.EXTRAORDINARY_SWING_PCT}% são marcadas como extraordinárias.
    </p>
    {section(
        "Valor de crédito SADIPEM aprovado (\"Deferido*\")",
        "Histórico completo 2002+ (arquivo único consolidado).",
        result["sadipem_value"], fmt_money,
    )}
    {section(
        "Quantidade de operações SADIPEM aprovadas",
        "Histórico completo 2002+.",
        result["sadipem_count"], lambda v: f"{v:,.0f}",
    )}
    {section(
        "Transferências constitucionais recebidas",
        "Janela rolante de 12 anos (2016+).",
        result["transfers"], fmt_money,
    )}
    """


# ---------------------------------------------------------------------------
# Finalidades e credores
# ---------------------------------------------------------------------------

def build_purposes_and_creditors(result):
    def section(title, rows):
        # Number each row by its position (1 = highest value) rather than
        # looking it up with rows.index(row) — that does an O(n) equality
        # search per row and would misbehave if two rows ever compared equal.
        ranked_rows = [{**row, "rank": i} for i, row in enumerate(rows, start=1)]
        chart = svg_bar_chart(
            ranked_rows, label_key="label", value_key="value", value_fmt=fmt_money, label_width=210,
        )
        cols = [
            ("#", "rank", None),
            ("Descrição", "label", None),
            ("Valor aprovado", lambda r: r["value"], fmt_money),
            ("Participação", lambda r: r["share_pct"], lambda v: f"{v:.1f}%"),
            ("Operações", "operations", None),
        ]
        return f"<h3>{esc(title)}</h3>{chart}{table(cols, ranked_rows)}"

    return f"""
    <h2>Finalidades e credores — para que e com quem os estados se endividam</h2>
    <p class="note">
      Saber que estados tomam mais crédito quando recebem mais transferências não
      diz nada sobre <em>para que</em> serve esse dinheiro nem <em>quem</em> está
      emprestando. As colunas "Finalidade" e "Credor" do SADIPEM respondem isso —
      e "Tipo de credor" é a lente de mais alto nível, já que "Credor" sozinho tem
      dezenas de instituições distintas. Mostra o top {purposes_and_creditors.TOP_N}
      de cada categoria por valor total aprovado, entre as
      {result['total_count']:,} operações ("Deferido*") que somam {fmt_money(result['total_value'])}.
    </p>
    {section("Finalidade (Finalidade)", result["finalidade"])}
    {section("Tipo de credor — categorias mais amplas", result["tipo_credor"])}
    {section("Credor — instituições específicas", result["credor"])}
    """


# ---------------------------------------------------------------------------
# Taxas de aprovação
# ---------------------------------------------------------------------------

def build_approval_rates(result):
    overall = result["overall"]
    total = result["total"]
    overall_rows = [
        {"bucket": bucket, "count": count, "share_pct": 100 * count / total}
        for bucket, count in sorted(overall.items(), key=lambda kv: -kv[1])
    ]
    overall_chart = svg_bar_chart(
        overall_rows, label_key="bucket", value_key="count",
        value_fmt=lambda v: f"{v:,}", label_width=110,
    )
    year_cols = [
        ("Ano", "year", None),
        ("Solicitações", "requests", None),
        ("Taxa de aprovação", lambda r: r["rate"], lambda v: f"{v:.1f}%"),
        ("Vs. nacional", lambda r: r["vs_national"], lambda v: (
            "▲ acima da média" if v == "above" else "▼ abaixo da média" if v == "below" else "— média"
        )),
    ]
    uf_chart = svg_bar_chart(
        result["by_uf"], label_key="uf", value_key="rate",
        value_fmt=lambda v: f"{v:.1f}%", label_width=50,
        highlight=lambda r: abs(r["diff_pp"]) > approval_rates.ABOVE_BELOW_AVERAGE_PP,
    )
    uf_cols = [
        ("UF", "uf", None),
        ("Solicitações", "requests", None),
        ("Taxa de aprovação", lambda r: r["rate"], lambda v: f"{v:.1f}%"),
        ("Diferença (p.p.)", lambda r: r["diff_pp"], lambda v: f"{v:+.1f}"),
    ]
    row_class = lambda r: "flag-extraordinary" if abs(r["diff_pp"]) > approval_rates.ABOVE_BELOW_AVERAGE_PP else ""
    return f"""
    <h2>Taxas de aprovação — quão seletivo é o processo, e como isso muda</h2>
    <p class="note">
      A coluna "Status" registra o desfecho de cada solicitação: Deferido (aprovado),
      Indeferido (negado), Arquivado (arquivado/retirado), entre outros mais raros.
      Olhar só para operações aprovadas (como as outras análises fazem) esconde o
      outro lado da história — quão seletivo é o processo, e se essa seletividade
      muda com o clima político e econômico (ex.: maior rigor em anos eleitorais,
      ou maior flexibilidade durante uma crise). Estados com pelo menos
      {approval_rates.MIN_REQUESTS_FOR_UF_RATE} solicitações e desvio acima de
      {approval_rates.ABOVE_BELOW_AVERAGE_PP} p.p. da média nacional estão destacados.
    </p>
    <div class="metric-grid">
      <div class="metric-card">
        <div class="label">Total de solicitações analisadas</div>
        <div class="value">{total:,}</div>
      </div>
      <div class="metric-card">
        <div class="label">Taxa de aprovação nacional</div>
        <div class="value">{result['national_rate']:.1f}%</div>
      </div>
    </div>
    <h3>Composição geral por status</h3>
    {overall_chart}
    <h3>Taxa de aprovação por ano</h3>
    {table(year_cols, result["by_year"])}
    <h3>Taxa de aprovação por estado (mín. {approval_rates.MIN_REQUESTS_FOR_UF_RATE} solicitações)</h3>
    {uf_chart}
    {table(uf_cols, result["by_uf"], row_class=row_class)}
    """


# ---------------------------------------------------------------------------
# Pandemia
# ---------------------------------------------------------------------------

def build_pandemic(result):
    cards = []
    for m in result["metrics"]:
        fmt = m["fmt"]
        direction = "up" if m["deviation_pct"] > 0 else "down"
        flag_cls = " flag" if m["is_extraordinary"] else ""
        arrow = "▲" if m["deviation_pct"] > 0 else "▼"
        cards.append(f"""
          <div class="metric-card{flag_cls}">
            <div class="label">{esc(m['label'])}</div>
            <div class="value {direction}">{arrow} {m['deviation_pct']:+.1f}%</div>
            <div class="extra">
              base ({'/'.join(pandemic_spotlight.BASELINE_YEARS)}): {fmt.format(m['baseline'])} {esc(m['unit'])}
              → pandemia ({'/'.join(pandemic_spotlight.PANDEMIC_YEARS)}): {fmt.format(m['pandemic'])} {esc(m['unit'])}
            </div>
          </div>
        """)

    year_cols = [
        ("Ano", "year", None),
        ("Transferências", lambda r: r["transfers"], fmt_money),
        ("Valor SADIPEM aprovado", lambda r: r["sadipem_value"], fmt_money),
        ("Taxa de aprovação", lambda r: r["rate"], lambda v: f"{v:.1f}%"),
        ("Razão dívida/receita", lambda r: r["ratio"], lambda v: f"{v:.4f}"),
    ]
    row_class = lambda r: "flag-pandemic" if r["is_pandemic"] else ""

    return f"""
    <h2>⚠ Foco na pandemia — 2020-2021 como evento extraordinário</h2>
    <p class="note">
      Toda outra análise neste relatório trata os anos da janela de forma uniforme;
      esta deliberadamente não trata: a emergência de saúde pública de 2020 trouxe
      contração econômica súbita, ajuda federal emergencial (Auxílio Emergencial,
      suplementação ad-hoc do FPM/FPE) e uma corrida dos estados por crédito para
      cobrir o rombo — nada disso se encaixa no padrão normal ano a ano. Compara
      2020-2021 com os dois anos imediatamente antes e depois
      (uma "linha de base" de {'/'.join(pandemic_spotlight.BASELINE_YEARS)}) em
      cada ângulo coberto pelas outras análises, reportando o desvio percentual —
      desvios acima de {pandemic_spotlight.EXTRAORDINARY_DEVIATION_PCT}% (em módulo)
      são marcados como extraordinários (⚠).
    </p>
    <div class="metric-grid">{''.join(cards)}</div>
    <h3>Detalhe ano a ano</h3>
    {table(year_cols, result["by_year"], row_class=row_class)}
    """


# ---------------------------------------------------------------------------
# Assemble
# ---------------------------------------------------------------------------

def build_report():
    """Run every analysis's compute(), wrap each result in a tab, and render the page.

    This is the one place that ties the whole report together: each `build_*`
    function above turns one analysis's `compute()` output into that tab's
    HTML body, `panel()` pairs it with a tab label + small "chip" summary
    (e.g. "ρ 0.13", "top 12") shown in the tab bar, and `render_page` wraps
    the lot in the shared page shell (header, tab navigation, styling).
    Tabs appear in the order listed below — that's also the report's
    narrative order, roughly: the big picture first (overview, correlation),
    then progressively more specific lenses (per capita, debt exposure,
    trends, breakdowns, selectivity), ending with the pandemic as the
    extraordinary event that explains some of what came before.
    """
    corr = correlate.compute()
    pc = per_capita.compute()
    dtr = debt_to_revenue.compute()
    trd = trends.compute()
    purp = purposes_and_creditors.compute()
    appr = approval_rates.compute()
    pand = pandemic_spotlight.compute()

    years = corr["years"]
    panels = [
        panel("overview", "Visão geral", "Resumo", build_overview(corr, purp)),
        panel("correlate", "Correlação", f"ρ {corr['pooled']['value']['spearman']:.2f}", build_correlate(corr)),
        panel("per_capita", "Per Capita", f"{len(pc['transfers'])} UFs", build_per_capita(pc)),
        panel("debt_to_revenue", "Dívida/Receita", f"{len(dtr['years'])} anos", build_debt_to_revenue(dtr)),
        panel("trends", "Tendências", f"{years[0]}-{years[-1]}", build_trends(trd)),
        panel("purposes", "Finalidades/Credores", f"top {purposes_and_creditors.TOP_N}", build_purposes_and_creditors(purp)),
        panel("approval", "Aprovação", f"{appr['national_rate']:.0f}%", build_approval_rates(appr)),
        panel("pandemic", "Pandemia", "2020-21", build_pandemic(pand)),
    ]

    return render_page(
        title="Crédito estadual e transferências constitucionais — Brasil",
        subtitle="Cruzamento de dados públicos do SADIPEM (Tesouro Nacional) com transferências constitucionais aos estados",
        badges=[
            badge(f"Janela {years[0]}-{years[-1]}"),
            badge(f"{purp['total_count']:,} operações analisadas"),
            badge(f"{fmt_money(purp['total_value'])} em crédito aprovado"),
        ],
        panels=panels,
    )


def build_report_to(output):
    output = Path(output)
    output.write_text(build_report(), encoding="utf-8")
    return output


def main():
    output = build_report_to(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT)
    print(f"Report written to {output}")


if __name__ == "__main__":
    main()
