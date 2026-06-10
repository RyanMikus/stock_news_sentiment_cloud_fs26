from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.stock_service import (
    DEFAULT_WINDOW_LABEL,
    TIME_WINDOWS,
    fetch_stock_history,
    fetch_stock_info,
    get_ticker_display_name,
    get_window_config,
)


def _window_labels() -> list[str]:
    return [w["label"] for w in TIME_WINDOWS]


@st.cache_data(ttl=300)
def _cached_stock_info(ticker: str) -> dict:
    return fetch_stock_info(ticker)


def _fmt_price(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def _fmt_market_cap(value: float | None) -> str:
    if value is None:
        return "N/A"
    if value >= 1e12:
        return f"${value / 1e12:.2f}T"
    if value >= 1e9:
        return f"${value / 1e9:.2f}B"
    if value >= 1e6:
        return f"${value / 1e6:.2f}M"
    return f"${value:,.0f}"


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:+.2f}%"


def _render_metrics(close, info: dict) -> None:
    current = float(close.iloc[-1])
    start = float(close.iloc[0])
    pct_change = (current - start) / start * 100 if start != 0 else None
    period_high = float(close.max())
    period_low = float(close.min())
    market_cap = info.get("market_cap")

    cols = st.columns(5)
    with cols[0]:
        st.metric("Current Price", _fmt_price(current))
    with cols[1]:
        st.metric("Period Change", _fmt_pct(pct_change))
    with cols[2]:
        st.metric("Period High", _fmt_price(period_high))
    with cols[3]:
        st.metric("Period Low", _fmt_price(period_low))
    with cols[4]:
        st.metric("Market Cap", _fmt_market_cap(market_cap))



def render_stock_chart(
    ticker: str,
    total_salience: float,
    articles: list[dict],
) -> bool:
    """Returns True if chart was rendered, False if no data available."""
    session_key = f"stock_window_{ticker}"
    display_name = get_ticker_display_name(ticker)

    # Fetch before rendering — skip entirely if no data available
    current_label = st.session_state.get(session_key, DEFAULT_WINDOW_LABEL)
    window = get_window_config(current_label)
    df = fetch_stock_history(ticker, window["period"], window["interval"])
    if df is None:
        return False

    with st.container(border=True):
        header_col, window_col = st.columns([2, 5])

        with header_col:
            st.subheader(f"{ticker} · {display_name}")

        with window_col:
            selected = st.segmented_control(
                "Time window",
                options=_window_labels(),
                default=DEFAULT_WINDOW_LABEL,
                key=session_key,
                label_visibility="collapsed",
            )

        # Refetch if window changed
        selected_label = selected or DEFAULT_WINDOW_LABEL
        if selected_label != current_label:
            window = get_window_config(selected_label)
            df = fetch_stock_history(ticker, window["period"], window["interval"])
            if df is None:
                st.caption("No data available for this time window.")
                return

        close = df["Close"].round(2)
        is_up = close.iloc[-1] >= close.iloc[0]
        price_color = "#26a65b" if is_up else "#e74c3c"
        fill_color = "rgba(38, 166, 91, 0.1)" if is_up else "rgba(231, 76, 60, 0.1)"

        y_min = float(close.min())
        y_max = float(close.max())
        padding = (y_max - y_min) * 0.15 if y_max != y_min else y_max * 0.01

        pct_from_start = ((close - close.iloc[0]) / close.iloc[0] * 100).round(2)

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=close,
                mode="lines",
                name=ticker,
                line=dict(color=price_color, width=2),
                fill="tozeroy",
                fillcolor=fill_color,
                customdata=pct_from_start.values,
                hovertemplate=(
                    "<b>$%{y:.2f}</b>"
                    "  <span style='color:gray'>%{customdata:+.2f}%</span>"
                    "<extra></extra>"
                ),
            )
        )
        fig.update_layout(
            height=240,
            margin=dict(l=0, r=0, t=4, b=0),
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(
                range=[y_min - padding, y_max + padding],
                showgrid=True,
                gridcolor="rgba(128,128,128,0.2)",
                zeroline=False,
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True)

        info = _cached_stock_info(ticker)
        _render_metrics(close, info)

    return True



def render_stocks_from_articles(
    articles: list[dict] | None = None,
) -> None:
    articles = articles or []

    active_tickers = st.session_state.get("gemini_ranked_tickers")
    gemini_ran = st.session_state.get("gemini_tickers_run", False)

    if not active_tickers:
        if not gemini_ran:
            st.info("Open the Overview tab first to run the Gemini analysis.")
        else:
            analysis = st.session_state.get("gemini_analysis") or {}
            summary = analysis.get("summary", "")
            if summary.startswith("Analysis unavailable"):
                st.error(f"Gemini analysis failed — {summary}")
            else:
                st.info("No tradeable stocks or indices were detected in these articles.")
            if st.button("Re-run Gemini analysis", key="rerun_gemini_stocks"):
                for key in list(st.session_state.keys()):
                    if key.startswith("gemini_"):
                        del st.session_state[key]
                st.rerun()
        return

    no_data: list[str] = []
    for ticker, total_salience in active_tickers:
        rendered = render_stock_chart(ticker, total_salience, articles)
        if not rendered:
            no_data.append(ticker)

    shown = len(active_tickers) - len(no_data)

    if shown == 0 and no_data:
        st.warning(
            f"Gemini detected {len(no_data)} ticker(s) but could not load chart data: "
            f"**{', '.join(no_data)}**. "
            "The ticker symbol may be incorrect or temporarily unavailable from yfinance."
        )
    elif no_data:
        st.caption(
            f"{len(active_tickers)} stock(s) detected via Gemini · sorted by salience"
            f" · no data for: {', '.join(no_data)}"
        )
    else:
        st.caption(f"{len(active_tickers)} stock(s) detected via Gemini · sorted by salience")
