import streamlit as st
import pandas as pd
import plotly.express as px

from strategy import Config, generate_signals, build_positions, daily_summary
from data_source import load_price_history_from_csv, demo_mock_history

st.set_page_config(page_title="Daily PnL Dashboard", layout="wide")

DEFAULT_UNIVERSE = ['BRK-B', 'INTC', 'XOM', 'CVX', 'AA', 'F', 'GM', 'WFC', 'VLO', 'BAC']

st.title("Daily PnL Tracking — Value/Momentum Strategy")

with st.sidebar:
    st.header("Settings")
    universe = st.text_area("Universe (comma-separated)", ",".join(DEFAULT_UNIVERSE)).replace("\n","")
    universe = [u.strip() for u in universe.split(',') if u.strip()]

    notional = st.number_input("Portfolio notional", min_value=1000.0, value=100000.0, step=1000.0)
    value_52w = st.slider("Value: within X% of 52W low", min_value=0.0, max_value=0.5, value=0.15, step=0.01)
    mom = st.slider("Momentum: 5D perf >", min_value=0.0, max_value=0.2, value=0.02, step=0.005)
    rsi_ovb = st.slider("Overbought RSI(14) >", min_value=50, max_value=95, value=75, step=1)
    long_alloc = st.slider("LONG allocation", min_value=0.0, max_value=0.5, value=0.10, step=0.01)
    short_alloc = st.slider("SHORT/AVOID allocation", min_value=-0.5, max_value=0.0, value=-0.05, step=0.01)

    data_mode = st.radio("Data mode", ["CSV files (data/) ", "Demo synthetic data"], index=1)

cfg = Config(
    universe=universe,
    notional=float(notional),
    value_52w_threshold=float(value_52w),
    momentum_threshold=float(mom),
    rsi_overbought=float(rsi_ovb),
    long_allocation=float(long_alloc),
    short_allocation=float(short_alloc),
)

if data_mode.startswith("CSV"):
    history = load_price_history_from_csv(cfg.universe, data_dir='data')
    if len(history) == 0:
        st.warning("No CSV files found in ./data. Switch to demo mode or add data/TICKER.csv files.")
else:
    history = demo_mock_history(cfg.universe)

signals = generate_signals(history, cfg)
positions = build_positions(signals, cfg)
summary = daily_summary(signals, positions, cfg)

c1, c2, c3, c4 = st.columns(4)

c1.metric("Universe", f"{len(cfg.universe)}")
c2.metric("Active positions", f"{int(summary.loc[0,'Active_Positions'])}")
c3.metric("Net allocation", f"{summary.loc[0,'Net_Allocation_%']}%")
c4.metric("Total deployed", f"${summary.loc[0,'Total_Notional']:,.0f}")

st.subheader("Signal distribution")
if not signals.empty:
    dist = signals['Signal'].value_counts().reset_index()
    dist.columns = ['Signal','Count']
    fig = px.pie(dist, values='Count', names='Signal', hole=0.45)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No signals computed — check data.")

st.subheader("Signals")
st.dataframe(signals, use_container_width=True)

st.subheader("Positions")
st.dataframe(positions, use_container_width=True)

st.subheader("Daily summary")
st.dataframe(summary, use_container_width=True)

st.caption("Tip: For real data, place per-ticker CSVs under ./data with columns Date,Open,High,Low,Close,Volume.")
