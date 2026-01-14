import os
from datetime import datetime
import pandas as pd

from strategy import Config, generate_signals, build_positions, daily_summary
from data_source import load_price_history_from_csv

DEFAULT_UNIVERSE = ['BRK-B', 'INTC', 'XOM', 'CVX', 'AA', 'F', 'GM', 'WFC', 'VLO', 'BAC']

OUTPUT_DIR = os.environ.get('OUTPUT_DIR', 'outputs')
DATA_DIR = os.environ.get('DATA_DIR', 'data')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cfg = Config(universe=DEFAULT_UNIVERSE)
    hist = load_price_history_from_csv(cfg.universe, data_dir=DATA_DIR)

    signals = generate_signals(hist, cfg)
    positions = build_positions(signals, cfg)
    summary = daily_summary(signals, positions, cfg)

    signals.to_csv(os.path.join(OUTPUT_DIR, 'signals.csv'), index=False)
    positions.to_csv(os.path.join(OUTPUT_DIR, 'positions.csv'), index=False)

    # append summary history
    summary_path = os.path.join(OUTPUT_DIR, 'daily_summary.csv')
    if os.path.exists(summary_path):
        prev = pd.read_csv(summary_path)
        out = pd.concat([prev, summary], ignore_index=True)
    else:
        out = summary
    out.to_csv(summary_path, index=False)

    print(f"Wrote outputs to {OUTPUT_DIR} at {datetime.utcnow().isoformat()}Z")


if __name__ == '__main__':
    main()
