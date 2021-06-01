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
    def __init__(self,exchange_id,timeout=3000):
        # 交易所
        if exchange_id == 'binaance':
            self.exchange = ccxt.binance(
                {
                    'apikey': config.BINANCE_API_KEY,
                    'secrert': config.BINANCE_SECRET_KEY,
                }
            )
        elif exchange_id == 'okexpaper':
            self.exchange = ccxt.okexpaper(
                {
                    'apikey': config.OKEXPAPER_API_KEY,
                    'secrert': config.OKEXPAPER_SECRET_KEY,
                    'password': config.OKEXPAPER_PASSWORD,
                }
            )
        elif exchange_id == 'okex5':
            self.exchange = ccxt.okex5(
                {
                    'apikey': config.OKEX5_API_KEY,
                    'secrert': config.OKEX5_SECRET_KEY,
                    'password': config.OKEX5_PASSWORD,
                }
            )
        else:
            print('ERROR: exchange id \"%d\" is not supported.',exchange_id)

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


    in_position = False


    def check_buy_sell_signals(self, df):
        global in_position

        print("checking for buy and sell signals")
        print(df.tail(5))
        last_row_index = len(df.index) - 1
        previous_row_index = last_row_index - 1

        if not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index]:
            print("changed to uptrend, buy")
            if not in_position:
                order =self.exchange.create_market_buy_order('ETH/USD', 0.05)
                print(order)
                in_position = True
            else:
                print("already in position, nothing to do")

        if df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index]:
            if in_position:
                print("changed to downtrend, sell")
                order =self.exchange.create_market_sell_order('ETH/USD', 0.05)
                print(order)
                in_position = False
            else:
                print("You aren't in position, nothing to sell")

    def RDO(self): # Return data only
        print(f"Fetching new bars for {datetime.now().isoformat()}")
        bars =self.exchange.fetch_ohlcv('ETH/USDT', timeframe='1m', limit=100)
        df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        return df

    def run(self):
        supertrend_data = self.supertrend(self.RDO())
        self.check_buy_sell_signals(supertrend_data)


exchange_id='yourexchangid'
schedule.every(10).seconds.do(ccxt_bot(exchange_id).run)

while True:
    schedule.run_pending()
    time.sleep(1)




