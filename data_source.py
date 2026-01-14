import os
import pandas as pd
from datetime import datetime

# Expect per-ticker CSVs in data/ like data/AAPL.csv with columns: Date,Open,High,Low,Close,Volume

def load_price_history_from_csv(universe: list[str], data_dir: str = 'data') -> dict[str, pd.DataFrame]:
    out = {}
    for tkr in universe:
        path = os.path.join(data_dir, f"{tkr}.csv")
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path)
        # Normalize
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
            df = df.set_index('Date')
        out[tkr] = df
    return out


def demo_mock_history(universe: list[str], days: int = 260) -> dict[str, pd.DataFrame]:
    # Generates synthetic OHLC data for demo/testing.
    import numpy as np
    import pandas as pd
    from datetime import timedelta

    end = pd.Timestamp(datetime.utcnow().date())
    idx = pd.bdate_range(end=end, periods=days)

    out = {}
    rng = np.random.default_rng(42)
    for tkr in universe:
        px0 = rng.uniform(10, 200)
        rets = rng.normal(0, 0.01, size=len(idx))
        close = px0 * (1 + rets).cumprod()
        high = close * (1 + rng.uniform(0.0, 0.02, size=len(idx)))
        low = close * (1 - rng.uniform(0.0, 0.02, size=len(idx)))
        open_ = close * (1 + rng.normal(0, 0.003, size=len(idx)))
        vol = rng.integers(1_000_000, 10_000_000, size=len(idx))
        out[tkr] = pd.DataFrame({'Open': open_, 'High': high, 'Low': low, 'Close': close, 'Volume': vol}, index=idx)
    return out
