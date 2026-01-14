import pandas as pd
import numpy as np
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Config:
    universe: list
    notional: float = 100000
    value_52w_threshold: float = 0.15
    momentum_threshold: float = 0.02
    rsi_overbought: float = 75
    long_allocation: float = 0.10
    short_allocation: float = -0.05


def calc_rsi(close: pd.Series, period: int = 14) -> float:
    if len(close) < period + 1:
        return np.nan
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])


def compute_trend(close: pd.Series) -> tuple[str, float, float, float]:
    ma20 = float(close.tail(20).mean())
    ma50 = float(close.tail(50).mean())
    ma200 = float(close.tail(200).mean()) if len(close) >= 200 else np.nan

    last = float(close.iloc[-1])
    if last > ma20 > ma50:
        trend = 'BULLISH'
    elif last < ma20 < ma50:
        trend = 'BEARISH'
    else:
        trend = 'MIXED'
    return trend, ma20, ma50, ma200


def generate_signals(price_history: dict[str, pd.DataFrame], cfg: Config, asof: str | None = None) -> pd.DataFrame:
    if asof is None:
        asof = datetime.utcnow().strftime('%Y-%m-%d')

    out = []
    for tkr in cfg.universe:
        if tkr not in price_history or price_history[tkr].empty:
            continue
        df = price_history[tkr].copy()
        if 'Close' not in df.columns:
            continue

        close = df['Close'].dropna()
        if len(close) < 50:
            continue

        last = float(close.iloc[-1])
        low_52w = float(df['Low'].tail(252).min()) if 'Low' in df.columns else float(close.tail(252).min())
        high_52w = float(df['High'].tail(252).max()) if 'High' in df.columns else float(close.tail(252).max())
        dist_low = (last - low_52w) / low_52w if low_52w else np.nan

        value_ok = dist_low <= cfg.value_52w_threshold

        perf_5d = (last - float(close.iloc[-5])) / float(close.iloc[-5]) if len(close) >= 5 else np.nan
        mom_ok = perf_5d > cfg.momentum_threshold

        rsi = calc_rsi(close)
        overbought = (not np.isnan(rsi)) and (rsi > cfg.rsi_overbought)

        trend, ma20, ma50, ma200 = compute_trend(close)

        rationale = []
        if overbought:
            signal = 'AVOID'
            rationale.append(f'OVERBOUGHT (RSI {rsi:.1f} > {cfg.rsi_overbought})')
        elif mom_ok and trend in ('BULLISH','MIXED'):
            signal = 'LONG'
            rationale.append(f'MOMENTUM (5D {perf_5d:.2%} > {cfg.momentum_threshold:.0%})')
            rationale.append(f'TREND ({trend})')
        elif value_ok and trend != 'BEARISH':
            signal = 'LONG'
            rationale.append(f'VALUE ({dist_low:.1%} from 52W low ≤ {cfg.value_52w_threshold:.0%})')
            rationale.append(f'TREND ({trend})')
        elif trend == 'BEARISH':
            signal = 'SHORT'
            rationale.append('TREND (BEARISH)')
        else:
            signal = 'HOLD'
            rationale.append(f'TREND ({trend})')

        out.append({
            'Date': asof,
            'Ticker': tkr,
            'Close': round(last,2),
            'Signal': signal,
            'RSI_14': None if np.isnan(rsi) else round(rsi,1),
            'Perf_5D': None if np.isnan(perf_5d) else perf_5d,
            'Trend': trend,
            'MA20': None if np.isnan(ma20) else round(ma20,2),
            'MA50': None if np.isnan(ma50) else round(ma50,2),
            'MA200': None if np.isnan(ma200) else round(ma200,2),
            '52W_Low': round(low_52w,2),
            '52W_High': round(high_52w,2),
            'Distance_to_52W_Low': None if np.isnan(dist_low) else dist_low,
            'Rationale': ' | '.join(rationale)
        })

    sig = pd.DataFrame(out)
    if not sig.empty:
        sig = sig.sort_values(['Signal','Ticker'])
    return sig


def build_positions(signals: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    rows = []
    for _, r in signals.iterrows():
        sig = r['Signal']
        px = float(r['Close'])
        if sig == 'LONG':
            alloc = cfg.long_allocation
        elif sig in ('SHORT','AVOID'):
            alloc = cfg.short_allocation
        else:
            alloc = 0.0

        shares = int((cfg.notional * abs(alloc)) / px) if alloc != 0 else 0
        pos_val = shares * px

        rows.append({
            'Date': r['Date'],
            'Ticker': r['Ticker'],
            'Signal': sig,
            'Close': round(px,2),
            'Allocation_%': round(alloc*100,1),
            'Shares': shares,
            'Position_Value': round(pos_val,2),
            'Entry_Price': round(px,2),
            'Daily_PnL': 0.0,
            'Cumulative_PnL': 0.0,
            'Daily_Return_%': 0.0,
        })

    return pd.DataFrame(rows)


def daily_summary(signals: pd.DataFrame, positions: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    def count(s):
        return int((signals['Signal'] == s).sum()) if not signals.empty else 0

    net_alloc = float(positions['Allocation_%'].sum()) if not positions.empty else 0.0
    total_notional = float(positions['Position_Value'].sum()) if not positions.empty else 0.0

    row = {
        'Date': datetime.utcnow().strftime('%Y-%m-%d'),
        'Universe_Size': len(cfg.universe),
        'Long_Signals': count('LONG'),
        'Short_Signals': count('SHORT'),
        'Avoid_Signals': count('AVOID'),
        'Hold_Signals': count('HOLD'),
        'Active_Positions': int((positions['Shares'] != 0).sum()) if not positions.empty else 0,
        'Net_Allocation_%': round(net_alloc,1),
        'Total_Notional': round(total_notional,2),
        'Daily_PnL': 0.0,
        'Cumulative_PnL': 0.0,
        'Portfolio_Return_%': 0.0,
        'Win_Rate_%': 0.0,
    }
    return pd.DataFrame([row])
