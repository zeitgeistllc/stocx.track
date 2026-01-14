#!/usr/bin/env python3
"""
Daily PnL Tracking Automation
Runs daily at 17:00 UTC (post-US close)
Generates signals, positions, summary, and updates dashboard
"""

import os
import sys
import json
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from typing import Dict, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_pnl.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

UNIVERSE = ['BRK-B', 'INTC', 'XOM', 'CVX', 'AA', 'F', 'GM', 'WFC', 'VLO', 'BAC']
NOTIONAL = 100000
VALUE_PE_THRESHOLD = 15
VALUE_52W_THRESHOLD = 0.15
MOMENTUM_THRESHOLD = 0.02
RSI_OVERBOUGHT = 75
LONG_ALLOCATION = 0.10
SHORT_ALLOCATION = -0.05

# Email configuration (optional)
EMAIL_ENABLED = False  # Set to True to enable email alerts
EMAIL_FROM = "your-email@example.com"
EMAIL_PASSWORD = "your-app-password"
EMAIL_TO = ["portfolio-alerts@example.com"]
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Output directory
OUTPUT_DIR = "./daily_pnl_outputs"

# ============================================================================
# STRATEGY ANALYZER CLASS
# ============================================================================

class StrategyAnalyzer:
    """Analyzes portfolio signals and generates daily reports"""

    def __init__(self, universe: List[str], notional: float):
        self.universe = universe
        self.notional = notional
        self.data = {}
        self.signals_df = None
        self.positions_df = None
        self.summary = {}

    def fetch_data(self):
        """
        Fetch latest data for universe
        CUSTOMIZE THIS for your data source:
        - yfinance (free, delayed)
        - Interactive Brokers API (real-time)
        - Alpha Vantage (requires API key)
        - CSV upload (manual)
        """
        logger.info(f"Fetching data for {len(self.universe)} tickers...")

        # PLACEHOLDER: Replace with your actual data source
        # Example with yfinance:
        # try:
        #     import yfinance as yf
        #     end_date = datetime.now().strftime('%Y-%m-%d')
        #     start_date = (datetime.now() - timedelta(days=250)).strftime('%Y-%m-%d')
        #     
        #     for ticker in self.universe:
        #         hist = yf.download(ticker, start=start_date, end=end_date, progress=False)
        #         if len(hist) > 0:
        #             self.data[ticker] = hist
        #             logger.info(f"✓ {ticker}")
        # except Exception as e:
        #     logger.error(f"Data fetch failed: {e}")
        #     return False

        logger.info(f"Using mock data (configure your data source in fetch_data())")
        return True

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI(14)"""
        if len(prices) < period + 1:
            return np.nan
        deltas = prices.diff()
        gains = (deltas.where(deltas > 0, 0)).rolling(window=period).mean()
        losses = (-deltas.where(deltas < 0, 0)).rolling(window=period).mean()
        rs = gains / losses
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    def generate_signals(self) -> pd.DataFrame:
        """Generate daily signals"""
        logger.info("Generating signals...")
        signals_list = []

        # MOCK DATA (replace with live data from fetch_data)
        mock_data = {
            'BRK-B': {'close': 415.32, 'rsi': 62.5, 'perf_5d': 0.015, 'low_52w': 380.0, 'high_52w': 445.0},
            'INTC': {'close': 28.45, 'rsi': 78.2, 'perf_5d': 0.038, 'low_52w': 18.5, 'high_52w': 32.0},
            'XOM': {'close': 118.92, 'rsi': 68.1, 'perf_5d': 0.022, 'low_52w': 85.0, 'high_52w': 125.0},
            'CVX': {'close': 145.67, 'rsi': 55.3, 'perf_5d': -0.008, 'low_52w': 110.0, 'high_52w': 160.0},
            'AA': {'close': 32.18, 'rsi': 71.9, 'perf_5d': 0.045, 'low_52w': 20.5, 'high_52w': 38.0},
            'F': {'close': 9.34, 'rsi': 48.2, 'perf_5d': -0.012, 'low_52w': 7.8, 'high_52w': 12.5},
            'GM': {'close': 43.21, 'rsi': 82.7, 'perf_5d': 0.061, 'low_52w': 28.0, 'high_52w': 48.0},
            'WFC': {'close': 78.94, 'rsi': 59.4, 'perf_5d': 0.018, 'low_52w': 65.0, 'high_52w': 92.0},
            'VLO': {'close': 142.55, 'rsi': 73.2, 'perf_5d': 0.035, 'low_52w': 92.0, 'high_52w': 155.0},
            'BAC': {'close': 34.67, 'rsi': 61.8, 'perf_5d': 0.012, 'low_52w': 28.0, 'high_52w': 40.0},
        }

        for ticker in self.universe:
            data = mock_data.get(ticker, {})
            close = data.get('close', 0)
            rsi = data.get('rsi', 50)
            perf_5d = data.get('perf_5d', 0)
            low_52w = data.get('low_52w', close)
            high_52w = data.get('high_52w', close)

            distance_to_low = (close - low_52w) / low_52w
            value_signal = distance_to_low <= VALUE_52W_THRESHOLD
            momentum_signal = perf_5d > MOMENTUM_THRESHOLD
            overbought = rsi > RSI_OVERBOUGHT
            trend = 'BULLISH' if np.random.random() > 0.6 else ('BEARISH' if np.random.random() > 0.5 else 'MIXED')

            # Signal logic
            signal_type = "HOLD"
            if overbought:
                signal_type = "AVOID"
            elif momentum_signal and trend in ["BULLISH", "MIXED"]:
                signal_type = "LONG"
            elif value_signal and trend != "BEARISH":
                signal_type = "LONG"
            elif trend == "BEARISH":
                signal_type = "SHORT"

            signals_list.append({
                'Date': datetime.now().strftime('%Y-%m-%d'),
                'Ticker': ticker,
                'Close': close,
                'Signal': signal_type,
                'RSI_14': round(rsi, 1),
                'Perf_5D': f"{perf_5d:.2%}",
                'Trend': trend,
                '52W_Low': round(low_52w, 2),
                '52W_High': round(high_52w, 2),
            })

        self.signals_df = pd.DataFrame(signals_list)
        logger.info(f"✓ Generated {len(self.signals_df)} signals")
        return self.signals_df

    def calculate_positions(self) -> pd.DataFrame:
        """Calculate model portfolio positions"""
        logger.info("Calculating positions...")
        positions_list = []

        for _, row in self.signals_df.iterrows():
            signal = row['Signal']
            close = row['Close']

            if signal == "LONG":
                allocation = LONG_ALLOCATION
            elif signal in ["SHORT", "AVOID"]:
                allocation = SHORT_ALLOCATION
            else:
                allocation = 0

            shares = int((self.notional * abs(allocation)) / close) if allocation != 0 else 0
            notional_position = shares * close

            positions_list.append({
                'Date': datetime.now().strftime('%Y-%m-%d'),
                'Ticker': row['Ticker'],
                'Signal': signal,
                'Close': round(close, 2),
                'Allocation_%': round(allocation * 100, 1),
                'Shares': shares,
                'Position_Value': round(notional_position, 2),
                'Entry_Price': round(close, 2),
                'Daily_PnL': 0.0,
                'Cumulative_PnL': 0.0,
                'Daily_Return_%': 0.0,
            })

        self.positions_df = pd.DataFrame(positions_list)
        logger.info(f"✓ Calculated {len(self.positions_df)} positions")
        return self.positions_df

    def generate_summary(self) -> Dict:
        """Generate portfolio summary"""
        logger.info("Generating summary...")

        long_count = len(self.signals_df[self.signals_df['Signal'] == 'LONG'])
        short_count = len(self.signals_df[self.signals_df['Signal'] == 'SHORT'])
        avoid_count = len(self.signals_df[self.signals_df['Signal'] == 'AVOID'])
        hold_count = len(self.signals_df[self.signals_df['Signal'] == 'HOLD'])

        total_notional = self.positions_df['Position_Value'].sum()
        net_allocation = self.positions_df['Allocation_%'].sum()

        self.summary = {
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Long_Signals': long_count,
            'Short_Signals': short_count,
            'Avoid_Signals': avoid_count,
            'Hold_Signals': hold_count,
            'Net_Allocation_%': round(net_allocation, 1),
            'Total_Notional': round(total_notional, 2),
            'Daily_PnL': 0.0,
            'Cumulative_PnL': 0.0,
            'Portfolio_Return_%': 0.0,
            'Active_Positions': len(self.positions_df[self.positions_df['Shares'] > 0]),
        }

        logger.info(f"✓ Summary generated: {long_count}L / {short_count}S / {avoid_count}A / {hold_count}H")
        return self.summary

    def export_results(self, output_dir: str = "."):
        """Export all results to CSV files"""
        os.makedirs(output_dir, exist_ok=True)

        # Export CSVs
        signals_path = os.path.join(output_dir, 'signals.csv')
        positions_path = os.path.join(output_dir, 'positions.csv')
        summary_path = os.path.join(output_dir, 'daily_summary.csv')
        history_path = os.path.join(output_dir, 'signal_history.csv')

        self.signals_df.to_csv(signals_path, index=False)
        self.positions_df.to_csv(positions_path, index=False)
        pd.DataFrame([self.summary]).to_csv(summary_path, index=False)

        logger.info(f"✓ Exported CSVs to {output_dir}")
        return {
            'signals': signals_path,
            'positions': positions_path,
            'summary': summary_path
        }

    def send_email_report(self):
        """Send daily email report (optional)"""
        if not EMAIL_ENABLED:
            return

        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_FROM
            msg['To'] = ', '.join(EMAIL_TO)
            msg['Subject'] = f"Daily PnL Report - {self.summary['Date']}"

            # Create email body
            body = f"""
Daily Portfolio Analysis - {self.summary['Date']}

SIGNAL SUMMARY:
  Long Signals:  {self.summary['Long_Signals']}
  Short Signals: {self.summary['Short_Signals']}
  Avoid Signals: {self.summary['Avoid_Signals']}
  Hold Signals:  {self.summary['Hold_Signals']}

PORTFOLIO METRICS:
  Net Allocation: {self.summary['Net_Allocation_%']}%
  Total Notional: ${self.summary['Total_Notional']:,.2f}
  Daily PnL:      ${self.summary['Daily_PnL']:,.2f}
  Return:         {self.summary['Portfolio_Return_%']:.4f}%
  Active Positions: {self.summary['Active_Positions']}

Files: Dashboard at ./daily_pnl_outputs/dashboard.html
"""

            msg.attach(MIMEText(body, 'plain'))

            # Send email
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()

            logger.info("✓ Email report sent")
        except Exception as e:
            logger.warning(f"Email send failed: {e}")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""
    logger.info("="*70)
    logger.info("DAILY PnL TRACKING - AUTOMATED EXECUTION")
    logger.info("="*70)

    try:
        # Initialize analyzer
        analyzer = StrategyAnalyzer(UNIVERSE, NOTIONAL)

        # Fetch data
        if not analyzer.fetch_data():
            logger.error("Data fetch failed")
            return 1

        # Generate signals and positions
        analyzer.generate_signals()
        analyzer.calculate_positions()
        analyzer.generate_summary()

        # Export results
        analyzer.export_results(OUTPUT_DIR)

        # Send email (optional)
        analyzer.send_email_report()

        logger.info("="*70)
        logger.info("✓ EXECUTION COMPLETE")
        logger.info("="*70)
        return 0

    except Exception as e:
        logger.error(f"Execution failed: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
