from __future__ import annotations

# ============================================================
# GEX RADAR BRASIL — STREAMLIT MULTI-HORIZONTE
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

    .block-container {
        max-width: 1800px;
        padding-top: 1.2rem;
        padding-bottom: 3rem;
    }

    .gex-header {
        border: 1px solid #334155;
        border-radius: 14px;
        padding: 18px 20px;
        background: linear-gradient(135deg, #111827 0%, #0f172a 100%);
        margin-bottom: 14px;
    }

    .gex-kicker {
        color: #38bdf8;
        font-size: 11px;
        font-weight: 900;
        letter-spacing: .08em;
        margin-bottom: 4px;
    }

    .gex-title-main {
        color: #f8fafc;
        font-size: 28px;
        font-weight: 900;
        line-height: 1.1;
    }

    .gex-subtitle-main {
        color: #94a3b8;
        font-size: 12px;
        margin-top: 8px;
        line-height: 1.5;
    }

    .instruction-box {
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 10px 12px;
        background: #111827;
        color: #cbd5e1;
        font-size: 12px;
        min-height: 42px;
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
@st.cache_resource(show_spinner=False)
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
    rows = []
    for _, row in summary.iterrows():
        out = {
            "Ativo": row["Ativo"],
            "Empresa": row["Empresa"],
            "Setor": row["Setor"],
            "Preço": moeda_br(row["Preço"]),
        }
        for horizon_label in core.HORIZON_ORDER:
            short = core.HORIZON_SHORT[horizon_label]
            wall_label = row.get(f"{short} Wall", "N/D")
            wall_price = row.get(f"{short} Wall Preço", np.nan)
            dist = row.get(f"{short} Dist %", np.nan)
            status = row.get(f"{short} Status", "SEM DADOS")
            quality = row.get(f"{short} Qualidade", np.nan)
            classe = row.get(f"{short} Classe", "N/D")

            if np.isfinite(wall_price):
                wall_text = f"{wall_label} • {moeda_br(wall_price)}"
            else:
                wall_text = str(wall_label)

            quality_text = (
                f"Q {core.br_number(quality, 1)} — {classe}"
                if np.isfinite(quality)
                else "Q N/D"
            )

            out[f"{short} Wall W1"] = wall_text
            out[f"{short} Dist."] = percentual_br(dist)
            out[f"{short} Status / Qualidade"] = f"{status} • {quality_text}"

        rows.append(out)
    return pd.DataFrame(rows)


def estilizar_tabela(df: pd.DataFrame):
    def status_style(value: Any) -> str:
        text = str(value)
        if "EM CIMA DO NÍVEL" in text:
            return "background-color:#dcfce7;color:#166534;font-weight:800;"
        if "MUITO PRÓXIMO" in text:
            return "background-color:#fef3c7;color:#92400e;font-weight:800;"
        if "PRÓXIMO" in text:
            return "background-color:#fff7ed;color:#9a3412;font-weight:800;"
        if "DISTANTE" in text:
            return "background-color:#f1f5f9;color:#475569;font-weight:700;"
        if "SEM DADOS" in text:
            return "background-color:#e5e7eb;color:#64748b;font-weight:700;"
        return ""

    styler = df.style
    status_cols = [c for c in df.columns if "Status / Qualidade" in c]
    if status_cols:
        styler = styler.map(status_style, subset=status_cols)
    styler = styler.set_properties(
        **{
            "text-align": "center",
            "white-space": "nowrap",
            "font-size": "12px",
        }
    )
    return styler


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
                • Call/Put W1 na triagem • W2/W3 no detalhe • Probability Engine removido
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
    st.rerun()


def renderizar_tabela() -> None:
    renderizar_cabecalho()

    coluna_botao, coluna_info = st.columns([1, 4])
    with coluna_botao:
        if st.button("🔄 ATUALIZAR DADOS B3", type="primary", use_container_width=True):
            atualizar_radar()
    with coluna_info:
        st.markdown(
            """
            <div class="instruction-box">
                A tabela já compara 30, 60, 90 e 180 dias simultaneamente.
                Clique em qualquer linha para abrir os detalhes do ativo.
            </div>
            """,
            unsafe_allow_html=True,
        )

    summary = core.summary_multi_horizon()
    display_df = preparar_tabela(summary)
    styler = estilizar_tabela(display_df)

    evento = st.dataframe(
        styler,
        width="stretch",
        height=min(960, 100 + 35 * len(display_df)),
        hide_index=True,
        key=f"gex_tabela_{st.session_state.versao_tabela}",
        on_select="rerun",
        selection_mode="single-row",
        row_height=34,
    )

    selecionadas = extrair_linhas_selecionadas(evento)
    if selecionadas:
        posicao = selecionadas[0]
        if 0 <= posicao < len(summary):
            st.session_state.ativo_selecionado = str(summary.iloc[posicao]["Ativo"])
            st.rerun()

    st.markdown(
        """
        <div class="gex-note-streamlit">
            <b>Ordenação:</b> menor distância absoluta a uma Wall W1 entre os quatro horizontes;
            em empate, maior qualidade do mesmo recorte. W2/W3 não entram nessa ordenação.
            <br><b>Proximidade:</b> ≤0,50% EM CIMA DO NÍVEL • ≤1,00% MUITO PRÓXIMO •
            ≤2,00% PRÓXIMO • acima de 2,00% DISTANTE.
            <br>A proximidade é estrutural e não representa compra, venda, suporte ou resistência.
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


def renderizar_slice(asset: str, horizon_label: str, exact_expiry, selected_view: str) -> None:
    chain, metrics = core.get_metrics(asset, horizon_label, exact_expiry)

    st.markdown(
        f'<div class="horizon-title">{horizon_label}</div>',
        unsafe_allow_html=True,
    )

    if metrics is None:
        st.info("Nenhum dado suficiente para esse recorte.")
        return

    st.markdown(
        core.cards_html(asset, metrics, horizon_label, exact_expiry),
        unsafe_allow_html=True,
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
        st.markdown(core.walls_detail_html(metrics), unsafe_allow_html=True)

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
        st.markdown(core.series_table_html(chain), unsafe_allow_html=True)

    elif selected_view == "Qualidade":
        st.markdown(core.quality_html(metrics), unsafe_allow_html=True)


def renderizar_detalhes(asset: str) -> None:
    topo_esquerda, topo_direita = st.columns([1, 4])
    with topo_esquerda:
        if st.button("← FECHAR DETALHES", type="primary", use_container_width=True):
            fechar_detalhes()
    with topo_direita:
        info = core.ASSET_INFO.get(asset, {"empresa": asset, "setor": "—"})
        st.markdown(
            f"""
            <div class="instruction-box">
                <b>{asset} — {info['empresa']}</b> • {info['setor']} •
                os quatro horizontes são exibidos em sequência, sem seletor de horizonte.
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
                    st.markdown(
                        core.cards_html(asset, metrics, horizon_label, None),
                        unsafe_allow_html=True,
                    )
        else:
            chain, metrics = core.get_metrics(asset, "180 dias", exact_expiry)
            if metrics is not None:
                st.markdown(
                    core.cards_html(asset, metrics, "180 dias", exact_expiry),
                    unsafe_allow_html=True,
                )
        st.markdown(core.methodology_html(), unsafe_allow_html=True)
        return

    if exact_expiry is not None:
        st.info(
            "Modo de investigação por vencimento específico: o cálculo abaixo usa somente "
            "as séries desse vencimento dentro do universo máximo de 180 dias."
        )
        renderizar_slice(asset, "180 dias", exact_expiry, selected_view)
        return

    for horizon_label in core.HORIZON_ORDER:
        renderizar_slice(asset, horizon_label, None, selected_view)


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
