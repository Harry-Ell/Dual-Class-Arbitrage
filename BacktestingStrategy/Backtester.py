import backtrader as bt
from datetime import datetime as dt, timedelta
import pytz
import alpaca_trade_api as tradeapi
from dotenv import load_dotenv
import os
from dual_class_arb import DualListedArbitrage

# Loading credentials for access to Alpaca
load_dotenv()
API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
BASE_URL = os.getenv('BASE_URL')
api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')

def fetch_data(symbol, timeframe, start_date, end_date):
    barset = api.get_bars(symbol, timeframe, start=start_date, end=end_date).df
    return barset

def align_data(data0, data1):
    data0 = data0[~data0.index.duplicated(keep='first')]
    data1 = data1[~data1.index.duplicated(keep='first')]
    common_index = data0.index.intersection(data1.index)

    data0_ffill = data0.reindex(common_index).ffill().bfill()
    data1_ffill = data1.reindex(common_index).ffill().bfill()

    data0_aligned = data0_ffill.loc[common_index]
    data1_aligned = data1_ffill.loc[common_index]

    return data0_aligned, data1_aligned


def backtest(symbol_pair, start_date, end_date):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(DualListedArbitrage)

    data0 = fetch_data(symbol_pair[0], timeframe='5Min', start_date=start_date, end_date=end_date)
    data1 = fetch_data(symbol_pair[1], timeframe='5Min', start_date=start_date, end_date=end_date)
    
    data0, data1 = align_data(data0, data1)

    print(f"Length of aligned data0: {len(data0)}")
    print(f"Length of aligned data1: {len(data1)}")

    if data0 is not None and not data0.empty and data1 is not None and not data1.empty:
    
        data0_bt = bt.feeds.PandasData(dataname=data0)
        data1_bt = bt.feeds.PandasData(dataname=data1)

        cerebro.adddata(data0_bt, name=symbol_pair[0])
        cerebro.adddata(data1_bt, name=symbol_pair[1])
        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trade_analyzer")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe_ratio")

        # Run the backtest
        try:
            results = cerebro.run()
            strategy = results[0]

            # Extract and print results
            print("Final Portfolio Value: ${}".format(cerebro.broker.getvalue()))

            # Trade Analyzer
            trade_analyzer = strategy.analyzers.trade_analyzer.get_analysis()
            print("Trade Analyzer Results: \n")
            print(f"Total: {trade_analyzer['total']} \n")
            print(f"PnL: {trade_analyzer['pnl']} \n")
            print(f"Won: {trade_analyzer['won']} \n")
            print(f"Lost: {trade_analyzer['lost']} \n")
            try:
                print(f"Streak: {trade_analyzer['streak']} \n")
            except KeyError:
                pass

            # Sharpe Ratio
            sharpe_ratio = strategy.analyzers.sharpe_ratio.get_analysis()
            print("Sharpe Ratio:", sharpe_ratio['sharperatio'])

            # Plot the results
            cerebro.plot()
        except Exception as e:
            print(f"An error occurred during backtesting: {e}")
    else:
        print("No data fetched or data is empty")

    return cerebro

# Example usage
symbol_pair = ('GOOGL', 'GOOG')
eastern = pytz.timezone('US/Eastern')
now_utc = dt.now(pytz.utc)
now_eastern = now_utc.astimezone(eastern)
# populating inputs for data fetch
end_date = (now_eastern - timedelta(hours=12)).isoformat()
start_date = (now_utc - timedelta(days=90)).isoformat()

cerebro_out = backtest(symbol_pair, start_date, end_date)