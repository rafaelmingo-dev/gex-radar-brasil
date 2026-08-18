from __future__ import annotations

# ============================================================
# GEX RADAR BRASIL â€” STREAMLIT MULTI-HORIZONTE â€” V32 FINAL CONSOLIDADO â€” CORRIGIDO
# 30 / 60 / 90 / 180 dias simultÃ¢neos
# Motor matemÃ¡tico: V21 validada no Google Colab.
# Projeto separado do GARCH Radar Brasil.
# ============================================================

from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import streamlit as st

import gex_core as core


# ============================================================
# 1. CONFIGURAÃ‡ÃƒO DA PÃGINA
# ============================================================
st.set_page_config(
    page_title="GEX Radar Brasil",
    page_icon="ðŸ“Š",
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
# 2. ESTADO DA SESSÃƒO
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
    # refresh_token > 0 forÃ§a nova tentativa de download da sessÃ£o mais recente.
    return core.load_complete_bundle(force=refresh_token > 0)


def instalar_runtime():
    with st.spinner(
        "Buscando a Ãºltima sessÃ£o completa da B3 e calculando IV, Gamma, GEX e Walls..."
    ):
        series, metadata, history = carregar_bundle(st.session_state.refresh_token)
    core.initialize_runtime(series, metadata, history)
    return metadata


try:
    metadata = instalar_runtime()
except Exception as exc:
    st.error(
        "NÃ£o foi possÃ­vel montar uma sessÃ£o completa da B3 para o GEX Radar Brasil. "
        "O painel nÃ£o publica dados parciais ou arquivos incompletos."
    )
    st.exception(exc)
    st.stop()


# ============================================================
# 4. FORMATAÃ‡ÃƒO / TABELA
# ============================================================
def _numero_finito(value: Any) -> float:
    """Converte um valor para float finito; caso contrÃ¡rio devolve NaN."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return np.nan

    return number if np.isfinite(number) else np.nan


def moeda_br(value: float) -> str:
    number = _numero_finito(value)
    if not np.isfinite(number):
        return "â€”"
    return core.br_money(number)


def percentual_br(value: float) -> str:
    number = _numero_finito(value)
    if not np.isfinite(number):
        return "â€”"
    return core.br_pct(number)


def _preco_spot_fallback(asset: str) -> float:
    """
    Recupera o spot da prÃ³pria base GEX/B3 quando a coluna PreÃ§o nÃ£o vier no resumo.

    Prioridade:
    1) selected_spot_price da gex_series jÃ¡ carregada;
    2) spot das mÃ©tricas dos horizontes jÃ¡ calculÃ¡veis.

    NÃ£o consulta fonte externa e nÃ£o cria preÃ§o estimado.
    """
    if not asset or asset in {"â€”", "BTC-USD"}:
        return np.nan

    series = getattr(core, "gex_series", None)
    if isinstance(series, pd.DataFrame) and not series.empty:
        required = {"underlying_ticker", "selected_spot_price"}
        if required.issubset(series.columns):
            values = pd.to_numeric(
                series.loc[
                    series["underlying_ticker"].eq(asset),
                    "selected_spot_price",
                ],
                errors="coerce",
            )
            values = values[np.isfinite(values) & values.gt(0)]
            if not values.empty:
                return float(values.median())

    for horizon_label in core.HORIZON_ORDER:
        try:
            _chain, metrics = core.get_metrics(asset, horizon_label)
        except Exception:
            metrics = None

        if metrics is not None:
            spot = _numero_finito(metrics.get("spot", np.nan))
            if np.isfinite(spot) and spot > 0:
                return spot

    return np.nan


def preparar_tabela(summary: pd.DataFrame) -> pd.DataFrame:
    """
    Radar principal compacto, pensado para caber integralmente no desktop.

    Cada horizonte usa apenas duas colunas:
    - W1: identifica Call W1, Put W1 ou confluÃªncia Call/Put W1 e mostra o nÃ­vel;
    - SituaÃ§Ã£o: mostra proximidade e distÃ¢ncia percentual.

    W2/W3 permanecem integralmente disponÃ­veis no detalhe do ativo.

    A leitura do schema Ã© tolerante para que uma ausÃªncia pontual da coluna PreÃ§o
    nÃ£o derrube o painel. Quando necessÃ¡rio, o preÃ§o Ã© recuperado da mesma base
    B3/GEX instalada no runtime.
    """
    rows = []

    if summary is None or not isinstance(summary, pd.DataFrame):
        return pd.DataFrame()

    asset_info = getattr(core, "ASSET_INFO", {})

    for _, row in summary.iterrows():
        asset = str(row.get("Ativo", "â€”")).strip() or "â€”"
        info = asset_info.get(
            asset,
            {"empresa": asset, "setor": "â€”"},
        )

        empresa = row.get("Empresa", info.get("empresa", asset))
        setor = row.get("Setor", info.get("setor", "â€”"))

        if pd.isna(empresa):
            empresa = info.get("empresa", asset)
        if pd.isna(setor):
            setor = info.get("setor", "â€”")

        preco = _numero_finito(row.get("PreÃ§o", np.nan))
        if not np.isfinite(preco):
            preco = _preco_spot_fallback(asset)

        out = {
            "Ativo": asset,
            "Empresa": str(empresa),
            "Setor": str(setor),
            "PreÃ§o": moeda_br(preco),
        }

        for horizon_label in core.HORIZON_ORDER:
            short_raw = core.HORIZON_SHORT[horizon_label]
            short = short_raw.upper()

            wall_label = str(row.get(f"{short_raw} Wall", "N/D"))
            wall_price = _numero_finito(
                row.get(f"{short_raw} Wall PreÃ§o", np.nan)
            )
            dist = _numero_finito(
                row.get(f"{short_raw} Dist %", np.nan)
            )
            status = str(row.get(f"{short_raw} Status", "SEM DADOS"))

            if np.isfinite(wall_price):
                out[f"{short} Â· W1"] = (
                    f"{wall_label} â€¢ "
                    f"{moeda_br(wall_price).replace('R$ ', 'R$')}"
                )

                status_curto = status
                if status == "EM CIMA DO NÃVEL":
                    status_curto = "EM CIMA"
                elif status == "MUITO PRÃ“XIMO":
                    status_curto = "MUITO PRÃ“X."

                out[f"{short} Â· SituaÃ§Ã£o"] = (
                    f"{status_curto} â€¢ {percentual_br(dist)}"
                )
            else:
                out[f"{short} Â· W1"] = "â€”"
                out[f"{short} Â· SituaÃ§Ã£o"] = "SEM DADOS"

        rows.append(out)

    return pd.DataFrame(rows)


def estilizar_tabela(df: pd.DataFrame):
    """
    Colore somente a coluna SituaÃ§Ã£o de cada horizonte.
    W1, preÃ§o, empresa e setor permanecem neutros para reduzir poluiÃ§Ã£o visual.
    """
    def status_style(value: Any) -> str:
        text = str(value)

        if text.startswith("EM CIMA"):
            return "background-color:#fee2e2;color:#991b1b;font-weight:900;"
        if text.startswith("MUITO PRÃ“X."):
            return "background-color:#ffedd5;color:#9a3412;font-weight:900;"
        if text.startswith("PRÃ“XIMO"):
            return "background-color:#fef3c7;color:#92400e;font-weight:900;"
        if text.startswith("DISTANTE"):
            return "background-color:#f1f5f9;color:#475569;font-weight:800;"
        if text.startswith("SEM DADOS"):
            return "background-color:#e5e7eb;color:#64748b;font-weight:800;"

        return ""

    styler = df.style

    status_cols = [coluna for coluna in df.columns if coluna.endswith("Â· SituaÃ§Ã£o")]

    if status_cols:
        styler = styler.map(status_style, subset=status_cols)

    colunas_destaque = [coluna for coluna in ["Ativo", "PreÃ§o"] if coluna in df.columns]

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
    Larguras explÃ­citas em pixels para que nomes e quatro horizontes apareÃ§am completos
    no desktop sem depender de rolagem horizontal.
    """
    config = {
        "Ativo": st.column_config.TextColumn("Ativo", width=72),
        "Empresa": st.column_config.TextColumn("Empresa", width=170),
        "Setor": st.column_config.TextColumn("Setor", width=150),
        "PreÃ§o": st.column_config.TextColumn("PreÃ§o", width=88),
    }

    for horizon_label in core.HORIZON_ORDER:
        short = core.HORIZON_SHORT[horizon_label].upper()

        config[f"{short} Â· W1"] = st.column_config.TextColumn(
            f"{short} Â· W1",
            width=150,
            help="Call W1, Put W1 ou confluÃªncia Call/Put W1 e o nÃ­vel principal deste horizonte.",
        )

        config[f"{short} Â· SituaÃ§Ã£o"] = st.column_config.TextColumn(
            f"{short} Â· SituaÃ§Ã£o",
            width=128,
            help="ClassificaÃ§Ã£o de proximidade e distÃ¢ncia percentual atÃ© a W1 principal.",
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
# 5. CABEÃ‡ALHO E RADAR PRINCIPAL
# ============================================================
def renderizar_cabecalho() -> None:
    reference_date = pd.Timestamp(metadata["reference_date"]).strftime("%d/%m/%Y")
    st.markdown(
        f"""
        <div class="gex-header">
            <div class="gex-kicker">GEX â€¢ WALLS â€¢ B3 â€¢ FECHAMENTO</div>
            <div class="gex-title-main">GEX RADAR BRASIL â€” 30 â€¢ 60 â€¢ 90 â€¢ 180 DIAS</div>
            <div class="gex-subtitle-main">
                Base B3: {reference_date} â€¢ 21 ativos B3 monitorados + Bitcoin visÃ­vel como N/D
                â€¢ W1 na triagem principal â€¢ W2/W3 no detalhe
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
            "ðŸ”„ ATUALIZAR DADOS B3",
            type="primary",
            use_container_width=True,
        ):
            atualizar_radar()

    with coluna_info:
        st.markdown(
            """
            <div class="instruction-box">
                Faixas DTE independentes: 30D = 1â€“30 â€¢ 60D = 31â€“60 â€¢ 90D = 61â€“90 â€¢ 180D = 91â€“180, sem acumulaÃ§Ã£o.
                W1 no radar principal â€¢ W1/W2/W3 ao abrir o ativo. Clique em uma linha para abrir o ativo.
            </div>
            """,
            unsafe_allow_html=True,
        )

    summary = core.summary_multi_horizon()

    if not isinstance(summary, pd.DataFrame) or summary.empty:
        st.warning(
            "O motor GEX nÃ£o devolveu linhas suficientes para montar o radar nesta execuÃ§Ã£o."
        )
        return

    display_df = preparar_tabela(summary)

    if display_df.empty:
        st.warning(
            "O resumo foi calculado, mas nÃ£o foi possÃ­vel montar a tabela principal nesta execuÃ§Ã£o."
        )
        return

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

        if 0 <= posicao < len(display_df):
            st.session_state.ativo_selecionado = str(
                display_df.iloc[posicao]["Ativo"]
            )
            st.rerun()

    st.markdown(
        """
        <div class="gex-note-streamlit">
            <b>OrdenaÃ§Ã£o:</b> primeiro aparecem os ativos com menor distÃ¢ncia absoluta
            a uma Wall W1 em qualquer horizonte; em empate, prevalece a maior qualidade
            do mesmo recorte.
            <br><b>Status:</b> â‰¤0,50% EM CIMA DO NÃVEL â€¢ â‰¤1,00% MUITO PRÃ“XIMO â€¢
            â‰¤2,00% PRÃ“XIMO â€¢ acima de 2,00% DISTANTE.
            <br><b>Faixas DTE:</b> 1â€“30 / 31â€“60 / 61â€“90 / 91â€“180, independentes e sem sobreposiÃ§Ã£o.
            <br><b>Radar:</b> somente W1. <b>Detalhe do ativo:</b> W1, W2 e W3 completos.
            As cores indicam apenas proximidade estrutural, nÃ£o compra, venda, suporte ou resistÃªncia.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 6. DETALHE DO ATIVO
# ============================================================
VIEW_OPTIONS = [
    "PreÃ§o + NÃ­veis",
    "Net GEX / Strike",
    "Gross Gamma",
    "Vencimentos",
    "SÃ©ries",
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

    A versÃ£o principal usa st.html(), evitando que o parser Markdown interprete
    a indentaÃ§Ã£o interna dos <div> como bloco de cÃ³digo. HÃ¡ um fallback seguro:
    se st.html() nÃ£o estiver disponÃ­vel por qualquer motivo, cada linha Ã©
    desindentada antes de seguir para st.markdown(..., unsafe_allow_html=True).

    Isso preserva cards, Leitura RÃ¡pida, tabelas de Walls, SÃ©ries, Qualidade e
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


def cards_sem_leitura_rapida(
    asset: str,
    metrics: dict,
    horizon_label: str,
    exact_expiry,
) -> str:
    """
    MantÃ©m o cabeÃ§alho do recorte e os seis cards principais produzidos pelo motor,
    mas nÃ£o exibe o bloco "Leitura RÃ¡pida" no detalhe do ativo.

    Importante: nenhuma mÃ©trica Ã© recalculada ou descartada. A funÃ§Ã£o altera apenas
    a apresentaÃ§Ã£o do HTML retornado por core.cards_html(). As Walls W1/W2/W3,
    Gross Gamma, Net GEX Proxy, qualidade, sÃ©ries e demais cÃ¡lculos permanecem no
    motor e no detalhe apropriado.
    """
    html = str(
        core.cards_html(
            asset,
            metrics,
            horizon_label,
            exact_expiry,
        )
    )

    inicio = html.find('<div class="gex-quick">')
    fim = html.find('<div class="gex-grid">', inicio) if inicio >= 0 else -1

    if inicio >= 0 and fim > inicio:
        html = html[:inicio] + html[fim:]

    return html


def renderizar_grafico(fig) -> None:
    """
    Exibe os grÃ¡ficos um pouco menores e centralizados, conforme solicitado.
    Usa aproximadamente 86% da largura Ãºtil e nÃ£o altera nenhuma informaÃ§Ã£o do grÃ¡fico.
    """
    if fig is None:
        return

    _margem_esquerda, coluna_grafico, _margem_direita = st.columns([0.7, 8.6, 0.7])
    with coluna_grafico:
        st.pyplot(fig, use_container_width=True)


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
        cards_sem_leitura_rapida(
            asset,
            metrics,
            horizon_label,
            exact_expiry,
        )
    )

    if selected_view == "PreÃ§o + NÃ­veis":
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
                "HistÃ³rico COTAHIST indisponÃ­vel nesta execuÃ§Ã£o. "
                "Os cÃ¡lculos GEX e as Walls continuam disponÃ­veis."
            )
        else:
            renderizar_grafico(fig)
            core.plt.close(fig)
        renderizar_html(
            core.walls_detail_html(metrics)
        )

    elif selected_view == "Net GEX / Strike":
        fig = core.plot_net_gex_by_strike(asset, metrics)
        if fig is not None:
            renderizar_grafico(fig)
            core.plt.close(fig)

    elif selected_view == "Gross Gamma":
        fig = core.plot_gross_gamma_calls_puts(asset, metrics)
        if fig is not None:
            renderizar_grafico(fig)
            core.plt.close(fig)

    elif selected_view == "Vencimentos":
        fig = core.plot_by_expiry(asset, chain)
        if fig is None:
            st.info("NÃ£o hÃ¡ dados suficientes para o grÃ¡fico por vencimento.")
        else:
            renderizar_grafico(fig)
            core.plt.close(fig)

    elif selected_view == "SÃ©ries":
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
            "âœ– FECHAR ATIVO",
            type="primary",
            use_container_width=True,
            key="fechar_ativo_top",
        ):
            fechar_detalhes()
    with topo_direita:
        info = core.ASSET_INFO.get(asset, {"empresa": asset, "setor": "â€”"})
        st.markdown(
            f"""
            <div class="instruction-box">
                <b>{asset} â€” {info['empresa']}</b> â€¢ {info['setor']} â€¢
                os quatro horizontes sÃ£o exibidos em sequÃªncia. W1/W2/W3 permanecem disponÃ­veis no detalhe e nos grÃ¡ficos.
            </div>
            """,
            unsafe_allow_html=True,
        )

    if asset == "BTC-USD":
        st.info(
            "BTC-USD permanece visÃ­vel para espelhar a lista do GARCH, mas esta versÃ£o "
            "calcula GEX exclusivamente com cadeias de opÃ§Ãµes negociadas na B3."
        )
        return

    expiries = expiries_asset(asset)
    expiry_options = [None] + expiries

    # Uso diÃ¡rio do detalhe: mostra diretamente PreÃ§o + NÃ­veis.
    # Os motores e funÃ§Ãµes auxiliares de Net GEX/Strike, Gross Gamma, Vencimentos,
    # SÃ©ries, Qualidade e Metodologia continuam preservados no cÃ³digo e no core;
    # apenas o seletor visual foi retirado da tela para reduzir poluiÃ§Ã£o.
    selected_view = "PreÃ§o + NÃ­veis"

    coluna_vazia, col_expiry = st.columns([3, 1])
    with col_expiry:
        exact_expiry = st.selectbox(
            "Vencimento especÃ­fico",
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
                        cards_sem_leitura_rapida(
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
                    cards_sem_leitura_rapida(
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
            "âœ– FECHAR ATIVO",
            use_container_width=True,
            key="fechar_ativo_bottom_method",
        ):
            fechar_detalhes()

        return

    if exact_expiry is not None:
        st.info(
            "Modo de investigaÃ§Ã£o por vencimento especÃ­fico: o cÃ¡lculo abaixo usa somente "
            "as sÃ©ries desse vencimento dentro do universo mÃ¡ximo de 180 dias."
        )
        renderizar_slice(
            asset,
            "180 dias",
            exact_expiry,
            selected_view,
        )

        if st.button(
            "âœ– FECHAR ATIVO",
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
        "âœ– FECHAR ATIVO",
        use_container_width=True,
        key="fechar_ativo_bottom",
    ):
        fechar_detalhes()


# ============================================================
# 7. DIAGNÃ“STICO OPCIONAL
# ============================================================
def renderizar_diagnostico() -> None:
    with st.expander("Pacote de diagnÃ³stico opcional"):
        st.caption(
            "Gera os CSVs por horizonte, resumo multi-horizonte, sÃ©ries GEX, histÃ³rico B3 e metadados."
        )
        if st.button("Preparar pacote de diagnÃ³stico"):
            with st.spinner("Montando pacote..."):
                path = Path(core.build_export_package())
                st.session_state.diagnostico_bytes = path.read_bytes()
                st.session_state.diagnostico_nome = path.name

        if st.session_state.diagnostico_bytes is not None:
            st.download_button(
                "Baixar pacote de diagnÃ³stico",
                data=st.session_state.diagnostico_bytes,
                file_name=st.session_state.diagnostico_nome,
                mime="application/zip",
            )


# ============================================================
# 8. RENDERIZAÃ‡ÃƒO
# ============================================================
if st.session_state.ativo_selecionado is None:
    renderizar_tabela()
else:
    renderizar_cabecalho()
    renderizar_detalhes(st.session_state.ativo_selecionado)

renderizar_diagnostico()
