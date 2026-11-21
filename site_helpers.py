"""Display helpers for the strategy pages: stat tiles, signal tables and Plotly charts.

Reads the CSV / JSON files in data/ (exported separately, outputs only).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from IPython.display import HTML, display

DATA = Path(__file__).parent / "data"

# palette (reads on light and dark backgrounds)
C_STRAT = "#2563eb"
C_ALT = "#14b8a6"
C_BENCH = "#9ca3af"
C_LONG = "#16a34a"
C_SHORT = "#dc2626"
C_FLAT = "#9ca3af"
C_PRICE = "#f59e0b"
AXIS = "#8b93a1"
GRID = "rgba(139,147,161,0.18)"

BTC_REGIMES = {"b": "Bullish", "bn": "Bullish-neutral", "n": "Neutral", "sn": "Bearish-neutral", "s": "Bearish"}


# ----------------------------------------------------------------- loading
def meta() -> dict:
    return json.loads((DATA / "meta.json").read_text())


def load_signals(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / f"{name}_signals.csv", parse_dates=["date"])


def load_backtest(name: str) -> pd.DataFrame:
    if name == "dca":
        r = pd.read_csv(DATA / "dca_backtest_weekly_returns.csv", parse_dates=["date"], index_col="date")
        eq = (1 + r).cumprod()
        first = eq.index[0] - pd.Timedelta(days=7)
        return pd.concat([pd.DataFrame(1.0, index=[first], columns=eq.columns), eq])
    return pd.read_csv(DATA / f"{name}_backtest.csv", parse_dates=["date"], index_col="date")


# ------------------------------------------------------------------- stats
def perf_stats(eq: pd.Series, periods: int) -> dict:
    r = eq.pct_change().dropna()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / years) - 1
    vol = r.std() * np.sqrt(periods)
    mdd = (eq / eq.cummax() - 1).min()
    return {"CAGR": cagr, "Volatility": vol, "Sharpe": (r.mean() * periods) / vol if vol else np.nan,
            "Max drawdown": mdd, "Calmar": cagr / abs(mdd) if mdd else np.nan}


def stat_tiles(items: list[tuple[str, str, str]]):
    """items: (label, value, css-modifier)."""
    tiles = "".join(f'<div class="stat {mod}"><span>{k}</span><b>{v}</b></div>' for k, v, mod in items)
    display(HTML(f'<div class="stats">{tiles}</div>'))


def perf_table(eqs: dict[str, pd.Series], periods: int, extra: dict | None = None):
    rows = {name: perf_stats(s.dropna(), periods) for name, s in eqs.items()}
    df = pd.DataFrame(rows).T
    fmt = {"CAGR": "{:+.1%}", "Volatility": "{:.1%}", "Sharpe": "{:.2f}", "Max drawdown": "{:.1%}", "Calmar": "{:.2f}"}
    if extra:
        for col, vals in extra.items():
            df[col] = pd.Series(vals)
            fmt[col] = "{:.0%}"
    html = (df.style.format(fmt, na_rep="–")
            .set_table_attributes('class="table table-sm perf-table"').to_html())
    display(HTML(html))


# ------------------------------------------------------------------ charts
def _layout(fig: go.Figure, height=380, yfmt=None, ylog=False, legend=True):
    fig.update_layout(
        height=height, margin=dict(l=8, r=8, t=30, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", size=12, color=AXIS),
        hovermode="x unified", showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickformat=yfmt)
    if ylog:
        fig.update_yaxes(type="log")
    return fig


def _show(fig):
    fig.show(config={"displayModeBar": False, "responsive": True})


START_VALUE = 100_000
WINDOWS = [("1Y", 1), ("3Y", 3), ("5Y", 5), ("All", None)]


def _rebased(s: pd.Series, years: int | None) -> pd.Series:
    """Slice the last `years` of the series and rebase so the window starts at START_VALUE."""
    s = s.dropna()
    if years is not None:
        s = s[s.index >= s.index[-1] - pd.DateOffset(years=years)]
    return s / s.iloc[0] * START_VALUE


def equity_chart(eqs: dict[str, tuple[pd.Series, str, dict]], ylog=True, height=400):
    """Growth of $100,000. The 1Y / 3Y / 5Y / All buttons re-slice the data and restart every line at $100,000.

    eqs: name -> (series, color, extra trace kwargs). ylog applies to the full-history view;
    the shorter windows use a linear axis, which reads better over a few years.
    """
    fig = go.Figure()
    names = list(eqs)
    for name, (s, color, kw) in eqs.items():
        kw = dict(kw)
        r = _rebased(s, None)
        fig.add_scatter(x=r.index, y=r.values, name=name, line=dict(color=color, width=kw.pop("width", 2),
                        dash=kw.pop("dash", None)), hovertemplate="$%{y:,.0f}", **kw)

    buttons = []
    for label, years in WINDOWS:
        xs, ys = [], []
        for name in names:
            r = _rebased(eqs[name][0], years)
            xs.append(r.index.strftime("%Y-%m-%d").tolist())
            ys.append([round(v, 2) for v in r.values.tolist()])
        log = ylog and years is None
        buttons.append(dict(label=label, method="update",
                            args=[{"x": xs, "y": ys},
                                  {"xaxis.autorange": True, "yaxis.autorange": True,
                                   "yaxis.type": "log" if log else "linear",
                                   "yaxis.title.text": f"Growth of ${START_VALUE:,}" + (" (log)" if log else "")}]))

    _layout(fig, height, ylog=ylog)
    fig.update_yaxes(title_text=f"Growth of ${START_VALUE:,}" + (" (log)" if ylog else ""), tickformat="$,.0f")
    fig.update_layout(
        margin=dict(l=8, r=8, t=56, b=8),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        updatemenus=[dict(type="buttons", direction="left", buttons=buttons, active=len(WINDOWS) - 1,
                          showactive=True, x=1, xanchor="right", y=1.13, yanchor="bottom",
                          pad=dict(r=0, t=0), bgcolor="rgba(139,147,161,0.12)", bordercolor=GRID,
                          font=dict(color=AXIS, size=11))])
    _show(fig)


def drawdown_chart(eqs: dict[str, tuple[pd.Series, str]], height=240):
    fig = go.Figure()
    for name, (s, color) in eqs.items():
        dd = s / s.cummax() - 1
        fig.add_scatter(x=dd.index, y=dd.values, name=name, line=dict(color=color, width=1.4),
                        fill="tozeroy", fillcolor=_rgba(color, 0.15), hovertemplate="%{y:.1%}")
    _layout(fig, height, yfmt=".0%")
    fig.update_yaxes(title_text="Drawdown")
    _show(fig)


def annual_returns_chart(eqs: dict[str, tuple[pd.Series, str]], height=300):
    fig = go.Figure()
    for name, (s, color) in eqs.items():
        yr = s.resample("YE").last()
        yr = pd.concat([s.iloc[:1], yr]).pct_change().dropna()
        fig.add_bar(x=yr.index.year, y=yr.values, name=name, marker_color=color, hovertemplate="%{y:.1%}")
    _layout(fig, height, yfmt=".0%")
    fig.update_layout(barmode="group", bargap=0.25, hovermode="x unified")
    fig.update_xaxes(dtick=1, tickangle=-45)
    _show(fig)


def _rgba(hex_color: str, a: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{a})"


def _position_shading(fig, df: pd.DataFrame):
    """Shade days by position: green = long (darker = larger), grey = flat."""
    dates = list(df["date"])
    for i, (d, p) in enumerate(zip(dates, df["position"])):
        x0 = d - pd.Timedelta(hours=12)
        x1 = (dates[i + 1] - pd.Timedelta(hours=12)) if i + 1 < len(dates) else d + pd.Timedelta(hours=12)
        color = _rgba(C_LONG, 0.08 + 0.14 * float(p)) if p > 0 else _rgba(C_FLAT, 0.07)
        fig.add_vrect(x0=x0, x1=x1, fillcolor=color, line_width=0, layer="below")


def recent_price_chart(df: pd.DataFrame, lines: dict[str, tuple[str, str, dict]], title_unit="", height=380):
    """Price over the latest signal window, with trend lines and position shading."""
    fig = go.Figure()
    _position_shading(fig, df)
    for col, (label, color, kw) in lines.items():
        fig.add_scatter(x=df["date"], y=df[col], name=label, line=dict(color=color, width=kw.get("width", 1.5),
                        dash=kw.get("dash")), mode="lines", hovertemplate="%{y:,.0f}")
    fig.add_scatter(x=df["date"], y=df["price"], name="Price", mode="lines+markers",
                    line=dict(color=C_PRICE, width=2.5), marker=dict(size=5), hovertemplate="%{y:,.2f}")
    _layout(fig, height, yfmt=",.0f")
    fig.update_yaxes(title_text=title_unit)
    fig.update_xaxes(tickformat="%b %d")
    _show(fig)


# ----------------------------------------------------------- signal widgets
def signal_card(label: str, position: float, asof: str, detail: str):
    if position >= 0.999:
        state, cls = "LONG", "long"
    elif position > 0:
        state, cls = f"PARTIAL {position:.0%}", "partial"
    else:
        state, cls = "FLAT", "flat"
    display(HTML(f"""
<div class="signal-card {cls}">
  <div class="sc-left"><span class="sc-label">{label}</span><span class="sc-state">{state}</span></div>
  <div class="sc-right"><span>Signal date</span><b>{asof}</b><span class="sc-detail">{detail}</span></div>
</div>"""))


def recent_signal_table(df: pd.DataFrame, regime_map: dict | None = None, extra_cols: dict | None = None):
    t = df.sort_values("date").copy()
    t["chg"] = t["position"].diff().fillna(0)          # change in held position vs prior day
    t = t.iloc[::-1]
    out = pd.DataFrame({"Date": t["date"].dt.strftime("%Y-%m-%d"), "Price": t["price"]})
    for col, label in (extra_cols or {}).items():
        out[label] = t[col]
    out["Regime"] = t["regime"].map(regime_map) if regime_map else t["regime"].str.replace("_", "-").str.capitalize()
    out["Position"] = t["position"]
    out["Change"] = t["chg"]

    def pos_style(v):
        c = C_LONG if v > 0 else C_FLAT
        return f"color:{c}; font-weight:600"

    def chg_fmt(v):
        return f"▲ buy {v:.0%}" if v > 0 else (f"▼ sell {-v:.0%}" if v < 0 else "")

    sty = (out.style.hide(axis="index")
           .format({"Price": "{:,.2f}", "Position": "{:.0%}", "Change": chg_fmt})
           .map(pos_style, subset=["Position"])
           .map(lambda v: f"color:{C_LONG if v > 0 else C_SHORT}; font-weight:600" if v else "", subset=["Change"])
           .set_table_attributes('class="table table-sm table-hover signal-table"'))
    display(HTML(f'<div class="table-scroll">{sty.to_html()}</div>'))


def dca_score_chart(df: pd.DataFrame, height=720):
    d = df.sort_values(["total_score", "rank"], ascending=[True, False])
    no_hold = d["no_hold"].astype(bool) if "no_hold" in d else pd.Series(False, index=d.index)
    colors = [C_LONG if p == 1 else C_SHORT if p == -1 else C_FLAT for p in d["pos"]]
    labels = {1: "Long", -1: "Short", 0: "No position"}
    status = ["No-hold list (ranked, not held)" if nh else labels[int(p)] for p, nh in zip(d["pos"], no_hold)]
    names = [f"{mk}  ({tk})" + (" ⊘" if nh else "") for mk, tk, nh in zip(d["market"], d["ticker"], no_hold)]
    fig = go.Figure(go.Bar(
        x=d["total_score"].astype(float).tolist(), y=names, orientation="h", marker_color=colors,
        marker_pattern_shape=["/" if nh else "" for nh in no_hold],
        customdata=[[s, float(r)] for s, r in zip(status, d["rank"])],
        hovertemplate="<b>%{y}</b><br>Total score %{x:.2f}<br>Rank %{customdata[1]:.0f} · %{customdata[0]}<extra></extra>"))
    _layout(fig, height, legend=False)
    fig.update_layout(hovermode="closest", margin=dict(l=8, r=8, t=10, b=8))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, zeroline=True, zerolinecolor=AXIS, title_text="Composite score (z)")
    _show(fig)


def dca_factor_table(df: pd.DataFrame):
    t = df.sort_values("rank").copy()
    if "no_hold" in t:
        t.loc[t["no_hold"].astype(bool), "pos"] = 9          # display code for "no-hold"
    t = t[["rank", "market", "ticker", "pos", "value", "quality", "growth", "momentum", "total_score"]]
    t = t.rename(columns={"rank": "Rank", "market": "Market", "ticker": "ETF", "pos": "Signal", "value": "Value",
                          "quality": "Quality", "growth": "Growth", "momentum": "Momentum", "total_score": "Total"})
    lab = {1: "LONG", -1: "SHORT", 0: "–", 9: "NO-HOLD"}

    def heat(v):
        if pd.isna(v):
            return ""
        a = min(abs(v) / 2.0, 1) * 0.55
        c = _rgba(C_LONG, a) if v > 0 else _rgba(C_SHORT, a)
        return f"background-color:{c}"

    sty = (t.style.hide(axis="index")
           .format({"Rank": "{:g}", "Signal": lambda v: lab.get(v, v),
                    **{c: "{:+.2f}" for c in ["Value", "Quality", "Growth", "Momentum", "Total"]}})
           .map(heat, subset=["Value", "Quality", "Growth", "Momentum", "Total"])
           .map(lambda v: f"color:{C_LONG if v == 1 else C_SHORT if v == -1 else C_FLAT}; font-weight:700",
                subset=["Signal"])
           .set_table_attributes('class="table table-sm table-hover signal-table factor-table"'))
    display(HTML(f'<div class="table-scroll">{sty.to_html()}</div>'))


def pct(v, signed=True):
    return f"{v:+.1%}" if signed else f"{v:.1%}"


# ------------------------------------------------------------ core portfolio
CORE_COLORS = {"Passive core": "#64748b", "Global Equity Rotation": C_STRAT, "Gold Trend": C_PRICE,
               "Bitcoin Trend": "#8b5cf6"}
CORE_SHORT = {"Global Equity Rotation": "Equity rotation", "Gold Trend": "Gold", "Bitcoin Trend": "Bitcoin"}


def allocation_bar(construction: list[dict], spread: float):
    """Stacked bar of the portfolio's building blocks, on a scale of total gross weight,
    with brackets for the capital (100%) and the financed part (above 100%)."""
    total = sum(c["weight"] for c in construction)
    segs = "".join(
        f'<div class="seg" style="flex:{c["weight"]};background:{CORE_COLORS.get(c["name"], C_BENCH)}" '
        f'title="{c["name"]}: {c["weight"]:.0%}"><b>{c["weight"]:.0%}</b><span>{CORE_SHORT.get(c["name"], c["name"])}</span></div>'
        for c in construction)
    fin = total - 1
    display(HTML(f"""
<div class="alloc">
  <div class="alloc-bar">{segs}</div>
  <div class="alloc-brackets">
    <div style="flex:1"><span>Capital · 100%</span></div>
    <div style="flex:{fin}" class="fin"><span>Financed · {fin:.0%} (fed funds + {spread:.0%})</span></div>
  </div>
  <p class="alloc-total">Gross exposure <b>{total:.0%}</b> of capital</p>
</div>"""))


def annual_returns_table(eqs: dict[str, pd.Series]):
    """Calendar-year returns, most recent year first; the current year is year-to-date."""
    cols = {}
    for name, s in eqs.items():
        yr = s.resample("YE").last()
        cols[name] = pd.concat([s.iloc[:1], yr]).pct_change().dropna().set_axis(yr.index.year)
    df = pd.DataFrame(cols).sort_index(ascending=False)
    df.index = [f"{y} YTD" if y == df.index.max() and s.index[-1].month < 12 else str(y) for y in df.index]
    df.index.name = "Year"
    names = list(eqs)
    if len(names) == 2:
        df["Difference"] = df[names[0]] - df[names[1]]

    def color(v):
        return "" if pd.isna(v) else f"color:{C_LONG if v > 0 else C_SHORT}"

    sty = (df.style.format("{:+.1%}", na_rep="–").map(color)
           .set_table_attributes('class="table table-sm table-hover perf-table annual-table"'))
    display(HTML(f'<div class="table-scroll">{sty.to_html()}</div>'))
