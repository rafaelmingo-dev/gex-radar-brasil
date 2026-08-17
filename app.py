from __future__ import annotations

# ============================================================
# GEX RADAR BRASIL — STREAMLIT MULTI-HORIZONTE — V30 FINAL AUDITADO
# 30 / 60 / 90 / 180 dias simultâneos
# Motor matemático: V21 validada no Google Colab.
# Projeto separado do GARCH Radar Brasil.
# ============================================================

from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import streamlit as st

import gex_core as core


# ============================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="GEX Radar Brasil",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS_APP = """
<style>
    .stApp {
        background: #0b1220;
        color: #e5e7eb;
    }

    header[data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
    }

    .block-container {
        max-width: 100vw !important;
        width: 100% !important;
        padding-top: 0.65rem !important;
        padding-right: 0.35rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.35rem !important;
        margin-top: 0 !important;
    }

    .gex-header {
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 16px 18px;
        background: linear-gradient(135deg, #111827 0%, #0f172a 100%);
        margin-bottom: 12px;
    }

    .gex-kicker {
        color: #38bdf8;
        font-size: 10px;
        font-weight: 900;
        letter-spacing: .08em;
        margin-bottom: 4px;
    }

    .gex-title-main {
        color: #f8fafc;
        font-size: 26px;
        font-weight: 900;
        line-height: 1.08;
    }

    .gex-subtitle-main {
        color: #94a3b8;
        font-size: 11px;
        margin-top: 7px;
        line-height: 1.45;
    }

    .instruction-box {
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 9px 11px;
        background: #111827;
        color: #cbd5e1;
        font-size: 11px;
        min-height: 40px;
    }

    .horizon-title {
        margin-top: 22px;
        margin-bottom: 7px;
        padding: 8px 11px;
        border-left: 4px solid #38bdf8;
        background: #111827;
        border-radius: 8px;
        color: #f8fafc;
        font-size: 18px;
        font-weight: 900;
    }

    .gex-note-streamlit {
        color: #94a3b8;
        font-size: 11px;
        line-height: 1.55;
        margin-top: 12px;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #334155;
        border-radius: 12px;
        overflow: hidden;
    }

    div[data-testid="stDataFrame"] * {
        font-family: Arial, Helvetica, sans-serif;
    }

    div.stButton > button,
    div[data-testid="stDownloadButton"] > button {
        font-weight: 800;
        border-radius: 10px;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""

st.markdown(CSS_APP, unsafe_allow_html=True)


# ============================================================
# 2. ESTADO DA SESSÃO
# ============================================================
if "ativo_selecionado" not in st.session_state:
    st.session_state.ativo_selecionado = None
if "versao_tabela" not in st.session_state:
    st.session_state.versao_tabela = 0
if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = 0
if "diagnostico_bytes" not in st.session_state:
    st.session_state.diagnostico_bytes = None
if "diagnostico_nome" not in st.session_state:
    st.session_state.diagnostico_nome = None


# ============================================================
# 3. CARGA / CACHE DA B3
# ============================================================
@st.cache_resource(show_spinner=False, max_entries=1)
def carregar_bundle(refresh_token: int):
    # refresh_token > 0 força nova tentativa de download da sessão mais recente.
    return core.load_complete_bundle(force=refresh_token > 0)


def instalar_runtime():
    with st.spinner(
        "Buscando a última sessão completa da B3 e calculando IV, Gamma, GEX e Walls..."
    ):
        series, metadata, history = carregar_bundle(st.session_state.refresh_token)
    core.initialize_runtime(series, metadata, history)
    return metadata


try:
    metadata = instalar_runtime()
except Exception as exc:
    st.error(
        "Não foi possível carregar o GEX Radar Brasil. "
        "A base anterior não foi substituída por dados incompletos."
    )
    st.exception(exc)
    st.stop()


# ============================================================
# 4. FORMATAÇÃO / TABELA
# ============================================================
def moeda_br(value: float) -> str:
    if value is None or not np.isfinite(value):
        return "—"
    return core.br_money(value)


def percentual_br(value: float) -> str:
    if value is None or not np.isfinite(value):
        return "—"
    return core.br_pct(value)


def preparar_tabela(summary: pd.DataFrame) -> pd.DataFrame:
    """
    Radar principal compacto, pensado para caber integralmente no desktop.

    Cada horizonte usa apenas duas colunas:
    - W1: identifica Call W1, Put W1 ou confluência Call/Put W1 e mostra o nível;
    - Situação: mostra proximidade e distância percentual.

    W2/W3 permanecem integralmente disponíveis no detalhe do ativo.
    """
    rows = []

    for _, row in summary.iterrows():
        out = {
            "Ativo": row["Ativo"],
            "Empresa": row["Empresa"],
            "Setor": row["Setor"],
            "Preço": moeda_br(row["Preço"]),
        }

        for horizon_label in core.HORIZON_ORDER:
            short_raw = core.HORIZON_SHORT[horizon_label]
            short = short_raw.upper()

            wall_label = str(row.get(f"{short_raw} Wall", "N/D"))
            wall_price = row.get(f"{short_raw} Wall Preço", np.nan)
            dist = row.get(f"{short_raw} Dist %", np.nan)
            status = str(row.get(f"{short_raw} Status", "SEM DADOS"))

            if np.isfinite(wall_price):
                out[f"{short} · W1"] = f"{wall_label} • {moeda_br(wall_price).replace('R$ ', 'R$')}"

                status_curto = status
                if status == "EM CIMA DO NÍVEL":
                    status_curto = "EM CIMA"
                elif status == "MUITO PRÓXIMO":
                    status_curto = "MUITO PRÓX."

                out[f"{short} · Situação"] = f"{status_curto} • {percentual_br(dist)}"
            else:
                out[f"{short} · W1"] = "—"
                out[f"{short} · Situação"] = "SEM DADOS"

        rows.append(out)

    return pd.DataFrame(rows)


def estilizar_tabela(df: pd.DataFrame):
    """
    Colore somente a coluna Situação de cada horizonte.
    W1, preço, empresa e setor permanecem neutros para reduzir poluição visual.
    """
    def status_style(value: Any) -> str:
        text = str(value)

        if text.startswith("EM CIMA"):
            return "background-color:#fee2e2;color:#991b1b;font-weight:900;"
        if text.startswith("MUITO PRÓX."):
            return "background-color:#ffedd5;color:#9a3412;font-weight:900;"
        if text.startswith("PRÓXIMO"):
            return "background-color:#fef3c7;color:#92400e;font-weight:900;"
        if text.startswith("DISTANTE"):
            return "background-color:#f1f5f9;color:#475569;font-weight:800;"
        if text.startswith("SEM DADOS"):
            return "background-color:#e5e7eb;color:#64748b;font-weight:800;"

        return ""

    styler = df.style

    status_cols = [coluna for coluna in df.columns if coluna.endswith("· Situação")]

    if status_cols:
        styler = styler.map(status_style, subset=status_cols)

    colunas_destaque = [coluna for coluna in ["Ativo", "Preço"] if coluna in df.columns]

    if colunas_destaque:
        styler = styler.set_properties(subset=colunas_destaque, **{"font-weight": "800"})

    styler = styler.set_properties(
        **{
            "text-align": "center",
            "white-space": "nowrap",
            "font-size": "10.5px",
        }
    )

    return styler


def montar_column_config() -> dict:
    """
    Larguras explícitas em pixels para que nomes e quatro horizontes apareçam completos
    no desktop sem depender de rolagem horizontal.
    """
    config = {
        "Ativo": st.column_config.TextColumn("Ativo", width=72),
        "Empresa": st.column_config.TextColumn("Empresa", width=170),
        "Setor": st.column_config.TextColumn("Setor", width=150),
        "Preço": st.column_config.TextColumn("Preço", width=88),
    }

    for horizon_label in core.HORIZON_ORDER:
        short = core.HORIZON_SHORT[horizon_label].upper()

        config[f"{short} · W1"] = st.column_config.TextColumn(
            f"{short} · W1",
            width=150,
            help="Call W1, Put W1 ou confluência Call/Put W1 e o nível principal deste horizonte.",
        )

        config[f"{short} · Situação"] = st.column_config.TextColumn(
            f"{short} · Situação",
            width=128,
            help="Classificação de proximidade e distância percentual até a W1 principal.",
        )

    return config


def extrair_linhas_selecionadas(evento: Any) -> list[int]:
    try:
        return list(evento.selection.rows)
    except Exception:
        try:
            return list(evento["selection"]["rows"])
        except Exception:
            return []


# ============================================================
# 5. CABEÇALHO E RADAR PRINCIPAL
# ============================================================
def renderizar_cabecalho() -> None:
    reference_date = pd.Timestamp(metadata["reference_date"]).strftime("%d/%m/%Y")
    st.markdown(
        f"""
        <div class="gex-header">
            <div class="gex-kicker">GEX • WALLS • B3 • FECHAMENTO</div>
            <div class="gex-title-main">GEX RADAR BRASIL — 30 • 60 • 90 • 180 DIAS</div>
            <div class="gex-subtitle-main">
                Base B3: {reference_date} • 21 ativos B3 monitorados + Bitcoin visível como N/D
                • W1 na triagem principal • W2/W3 no detalhe
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def atualizar_radar() -> None:
    st.session_state.ativo_selecionado = None
    st.session_state.versao_tabela += 1
    st.session_state.refresh_token += 1
    st.session_state.diagnostico_bytes = None
    st.session_state.diagnostico_nome = None
    carregar_bundle.clear()
    st.rerun()


def renderizar_tabela() -> None:
    renderizar_cabecalho()

    coluna_botao, coluna_info = st.columns([1, 4])

    with coluna_botao:
        if st.button(
            "🔄 ATUALIZAR DADOS B3",
            type="primary",
            use_container_width=True,
        ):
            atualizar_radar()

    with coluna_info:
        st.markdown(
            """
            <div class="instruction-box">
                30, 60, 90 e 180 dias lado a lado • W1 no radar principal • W1/W2/W3 ao abrir o ativo.
                Clique em uma linha para abrir o ativo.
            </div>
            """,
            unsafe_allow_html=True,
        )

    summary = core.summary_multi_horizon()
    display_df = preparar_tabela(summary)
    styler = estilizar_tabela(display_df)

    evento = st.dataframe(
        styler,
        column_config=montar_column_config(),
        width="stretch",
        height=min(
            980,
            100 + 35 * len(display_df),
        ),
        hide_index=True,
        key=f"gex_tabela_{st.session_state.versao_tabela}",
        on_select="rerun",
        selection_mode="single-row",
        row_height=34,
    )

    selecionadas = extrair_linhas_selecionadas(
        evento
    )

    if selecionadas:
        posicao = selecionadas[0]

        if 0 <= posicao < len(summary):
            st.session_state.ativo_selecionado = str(
                summary.iloc[posicao]["Ativo"]
            )
            st.rerun()

    st.markdown(
        """
        <div class="gex-note-streamlit">
            <b>Ordenação:</b> primeiro aparecem os ativos com menor distância absoluta
            a uma Wall W1 em qualquer horizonte; em empate, prevalece a maior qualidade
            do mesmo recorte.
            <br><b>Status:</b> ≤0,50% EM CIMA DO NÍVEL • ≤1,00% MUITO PRÓXIMO •
            ≤2,00% PRÓXIMO • acima de 2,00% DISTANTE.
            <br><b>Radar:</b> somente W1. <b>Detalhe do ativo:</b> W1, W2 e W3 completos.
            As cores indicam apenas proximidade estrutural, não compra, venda, suporte ou resistência.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 6. DETALHE DO ATIVO
# ============================================================
VIEW_OPTIONS = [
    "Preço + Níveis",
    "Net GEX / Strike",
    "Gross Gamma",
    "Vencimentos",
    "Séries",
    "Qualidade",
    "Metodologia",
]


def fechar_detalhes() -> None:
    st.session_state.ativo_selecionado = None
    st.session_state.versao_tabela += 1
    st.rerun()


def expiries_asset(asset: str) -> list[pd.Timestamp]:
    if asset == "BTC-USD" or core.gex_series.empty:
        return []
    values = (
        core.gex_series.loc[
            core.gex_series["underlying_ticker"].eq(asset),
            "maturity_date",
        ]
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    return [pd.Timestamp(v) for v in values]


def renderizar_html(fragmento: str) -> None:
    """
    Renderiza como HTML real os blocos produzidos pelo motor.

    A versão principal usa st.html(), evitando que o parser Markdown interprete
    a indentação interna dos <div> como bloco de código. Há um fallback seguro:
    se st.html() não estiver disponível por qualquer motivo, cada linha é
    desindentada antes de seguir para st.markdown(..., unsafe_allow_html=True).

    Isso preserva cards, Leitura Rápida, tabelas de Walls, Séries, Qualidade e
    Metodologia sem exibir tags HTML como texto na tela.
    """
    if fragmento is None:
        return

    html = str(fragmento).strip()

    if not html:
        return

    try:
        st.html(html)
    except Exception:
        html_fallback = "\n".join(
            linha.lstrip()
            for linha in html.splitlines()
        )
        st.markdown(
            html_fallback,
            unsafe_allow_html=True,
        )


def renderizar_slice(asset: str, horizon_label: str, exact_expiry, selected_view: str) -> None:
    chain, metrics = core.get_metrics(asset, horizon_label, exact_expiry)

    st.markdown(
        f'<div class="horizon-title">{horizon_label}</div>',
        unsafe_allow_html=True,
    )

    if metrics is None:
        st.info("Nenhum dado suficiente para esse recorte.")
        return

    renderizar_html(
        core.cards_html(
            asset,
            metrics,
            horizon_label,
            exact_expiry,
        )
    )

    if selected_view == "Preço + Níveis":
        trading_days = core.chart_trading_days_for_horizon(horizon_label)
        fig = core.plot_price_with_gex_levels(
            asset,
            metrics,
            trading_days,
            horizon_label,
            exact_expiry,
        )
        if fig is None:
            st.warning(
                "Histórico COTAHIST indisponível nesta execução. "
                "Os cálculos GEX e as Walls continuam disponíveis."
            )
        else:
            st.pyplot(fig, use_container_width=True)
            core.plt.close(fig)
        renderizar_html(
            core.walls_detail_html(metrics)
        )

    elif selected_view == "Net GEX / Strike":
        fig = core.plot_net_gex_by_strike(asset, metrics)
        if fig is not None:
            st.pyplot(fig, use_container_width=True)
            core.plt.close(fig)

    elif selected_view == "Gross Gamma":
        fig = core.plot_gross_gamma_calls_puts(asset, metrics)
        if fig is not None:
            st.pyplot(fig, use_container_width=True)
            core.plt.close(fig)

    elif selected_view == "Vencimentos":
        fig = core.plot_by_expiry(asset, chain)
        if fig is None:
            st.info("Não há dados suficientes para o gráfico por vencimento.")
        else:
            st.pyplot(fig, use_container_width=True)
            core.plt.close(fig)

    elif selected_view == "Séries":
        renderizar_html(
            core.series_table_html(chain)
        )

    elif selected_view == "Qualidade":
        renderizar_html(
            core.quality_html(metrics)
        )


def renderizar_detalhes(asset: str) -> None:
    topo_esquerda, topo_direita = st.columns([1, 4])
    with topo_esquerda:
        if st.button(
            "✖ FECHAR ATIVO",
            type="primary",
            use_container_width=True,
            key="fechar_ativo_top",
        ):
            fechar_detalhes()
    with topo_direita:
        info = core.ASSET_INFO.get(asset, {"empresa": asset, "setor": "—"})
        st.markdown(
            f"""
            <div class="instruction-box">
                <b>{asset} — {info['empresa']}</b> • {info['setor']} •
                os quatro horizontes são exibidos em sequência, sem seletor de horizonte. W1/W2/W3 permanecem disponíveis no detalhe e nos gráficos.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if asset == "BTC-USD":
        st.info(
            "BTC-USD permanece visível para espelhar a lista do GARCH, mas esta versão "
            "calcula GEX exclusivamente com cadeias de opções negociadas na B3."
        )
        return

    expiries = expiries_asset(asset)
    expiry_options = [None] + expiries

    col_view, col_expiry = st.columns([2, 1])
    with col_view:
        selected_view = st.radio(
            "Visualização",
            VIEW_OPTIONS,
            horizontal=True,
            key=f"view_{asset}",
        )
    with col_expiry:
        exact_expiry = st.selectbox(
            "Vencimento específico",
            expiry_options,
            index=0,
            format_func=lambda x: (
                "Todos os horizontes"
                if x is None
                else pd.Timestamp(x).strftime("%d/%m/%Y")
            ),
            key=f"expiry_{asset}",
        )

    if selected_view == "Metodologia":
        if exact_expiry is None:
            for horizon_label in core.HORIZON_ORDER:
                chain, metrics = core.get_metrics(asset, horizon_label)
                st.markdown(
                    f'<div class="horizon-title">{horizon_label}</div>',
                    unsafe_allow_html=True,
                )
                if metrics is not None:
                    renderizar_html(
                        core.cards_html(
                            asset,
                            metrics,
                            horizon_label,
                            None,
                        )
                    )
        else:
            chain, metrics = core.get_metrics(asset, "180 dias", exact_expiry)
            if metrics is not None:
                renderizar_html(
                    core.cards_html(
                        asset,
                        metrics,
                        "180 dias",
                        exact_expiry,
                    )
                )

        renderizar_html(
            core.methodology_html()
        )

        if st.button(
            "✖ FECHAR ATIVO",
            use_container_width=True,
            key="fechar_ativo_bottom_method",
        ):
            fechar_detalhes()

        return

    if exact_expiry is not None:
        st.info(
            "Modo de investigação por vencimento específico: o cálculo abaixo usa somente "
            "as séries desse vencimento dentro do universo máximo de 180 dias."
        )
        renderizar_slice(
            asset,
            "180 dias",
            exact_expiry,
            selected_view,
        )

        if st.button(
            "✖ FECHAR ATIVO",
            use_container_width=True,
            key="fechar_ativo_bottom_expiry",
        ):
            fechar_detalhes()

        return

    for horizon_label in core.HORIZON_ORDER:
        renderizar_slice(
            asset,
            horizon_label,
            None,
            selected_view,
        )

    if st.button(
        "✖ FECHAR ATIVO",
        use_container_width=True,
        key="fechar_ativo_bottom",
    ):
        fechar_detalhes()


# ============================================================
# 7. DIAGNÓSTICO OPCIONAL
# ============================================================
def renderizar_diagnostico() -> None:
    with st.expander("Pacote de diagnóstico opcional"):
        st.caption(
            "Gera os CSVs por horizonte, resumo multi-horizonte, séries GEX, histórico B3 e metadados."
        )
        if st.button("Preparar pacote de diagnóstico"):
            with st.spinner("Montando pacote..."):
                path = Path(core.build_export_package())
                st.session_state.diagnostico_bytes = path.read_bytes()
                st.session_state.diagnostico_nome = path.name

        if st.session_state.diagnostico_bytes is not None:
            st.download_button(
                "Baixar pacote de diagnóstico",
                data=st.session_state.diagnostico_bytes,
                file_name=st.session_state.diagnostico_nome,
                mime="application/zip",
            )


# ============================================================
# 8. RENDERIZAÇÃO
# ============================================================
if st.session_state.ativo_selecionado is None:
    renderizar_tabela()
else:
    renderizar_cabecalho()
    renderizar_detalhes(st.session_state.ativo_selecionado)

renderizar_diagnostico()
