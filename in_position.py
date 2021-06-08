import ccxt
import config
import schedule
import pandas as pd

pd.set_option('display.max_rows', None)

import warnings

warnings.filterwarnings('ignore')

import numpy as np
from datetime import datetime
import time


class ccxt_bot():
    def __init__(self, exchange_id, enable_KWARGS=False):
        self.in_position = False
        if enable_KWARGS:
            kwargs = config.KWARGS
        else:
            kwargs = {}
        # 交易所
        if exchange_id == 'binance':
            self.exchange = ccxt.binance(
                {
                    'apiKey': config.BINANCE_API_KEY,
                    'secret': config.BINANCE_SECRET_KEY,
                    **kwargs
                }
            )
        elif exchange_id == 'okexpaper':
            self.exchange = ccxt.okexpaper(
                {
                    'apiKey': config.OKEXPAPER_API_KEY,
                    'secret': config.OKEXPAPER_SECRET_KEY,
                    'password': config.OKEXPAPER_PASSWORD,
                    **kwargs
                }
            )
        elif exchange_id == 'okex5':
            self.exchange = ccxt.okex5(
                {
                    'apiKey': config.OKEX5_API_KEY,
                    'secret': config.OKEX5_SECRET_KEY,
                    'password': config.OKEX5_PASSWORD,
                    **kwargs
                }
            )
        elif exchange_id == 'huobipro':
            self.exchange = ccxt.huobipro(
                {
                    'apiKey': config.HUOBIPRO_API_KEY,
                    'secret': config.HUOBIPRO_SECRET_KEY,
                    **kwargs
                }
            )
        else:
            print('ERROR: exchange id \"%s\" is not supported.' % exchange_id)
            exit()

    def tr(self, data):
        data['previous_close'] = data['close'].shift(1)
        data['high-low'] = abs(data['high'] - data['low'])
        data['high-pc'] = abs(data['high'] - data['previous_close'])
        data['low-pc'] = abs(data['low'] - data['previous_close'])

        tr = data[['high-low', 'high-pc', 'low-pc']].max(axis=1)

        return tr

    def atr(self, data, period):
        data['tr'] = self.tr(data)
        atr = data['tr'].rolling(period).mean()

        return atr

    def supertrend(self, df, period=7, atr_multiplier=3):
        hl2 = (df['high'] + df['low']) / 2
        df['atr'] = self.atr(df, period)
        df['upperband'] = hl2 + (atr_multiplier * df['atr'])
        df['lowerband'] = hl2 - (atr_multiplier * df['atr'])
        df['in_uptrend'] = True

        for current in range(1, len(df.index)):
            previous = current - 1

            if df['close'][current] > df['upperband'][previous]:
                df['in_uptrend'][current] = True
            elif df['close'][current] < df['lowerband'][previous]:
                df['in_uptrend'][current] = False
            else:
                df['in_uptrend'][current] = df['in_uptrend'][previous]

                if df['in_uptrend'][current] and df['lowerband'][current] < df['lowerband'][previous]:
                    df['lowerband'][current] = df['lowerband'][previous]

                if not df['in_uptrend'][current] and df['upperband'][current] > df['upperband'][previous]:
                    df['upperband'][current] = df['upperband'][previous]

        return df

    def check_buy_sell_signals(self, df):
        print("checking for buy and sell signals")
        print(df.tail(5))
        last_row_index = len(df.index) - 1
        previous_row_index = last_row_index - 1

        if not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index]:
            print("changed to uptrend, buy")
            if not self.in_position:
                order = self.exchange.create_market_buy_order('ETH/USD', 0.05)
                print(order)
                self.in_position = True
            else:
                print("already in position, nothing to do")

        if df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index]:
            if self.in_position:
                print("changed to downtrend, sell")
                order = self.exchange.create_market_sell_order('ETH/USD', 0.05)
                print(order)
                self.in_position = False
            else:
                print("You aren't in position, nothing to sell")

    def rdo(self):  # Return data only
        print(f"Fetching new bars for {datetime.now().isoformat()}")
        bars = self.exchange.fetch_ohlcv('ETH/USDT', timeframe='1m', limit=100)
        df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        return df

    def run(self):
        supertrend_data = self.supertrend(self.rdo())
        self.check_buy_sell_signals(supertrend_data)


exchange_id = 'yourexchangeid'
# timeout=15000

schedule.every(10).seconds.do(ccxt_bot(exchange_id, True).run)

while True:
    schedule.run_pending()
    time.sleep(1)
