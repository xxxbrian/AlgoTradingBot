# 重构版三角套利
# TODO 加入挂单查询，对可盈利交易对进行分析
# TODO 短时间内多次查询，降低错误率
# TODO 根据利率和余额自动下单
import warnings

import ccxt
import sample_config as config

warnings.filterwarnings('ignore')


class interest():
    def __init__(self, exchange):
        self.ticks = exchange.fetch_tickers()
        self.ent_list = ['ETH', 'BTC', 'BNB']
        self.sums = 50
        self.poundage = 0.075
        self.dict = {}

        # ETH & BTC
        self.dict['ETH/BTC'] = self.ticks['ETH/BTC']['bid']
        self.dict['BTC/ETH'] = 1 / self.dict['ETH/BTC']

        # BNB & ETH
        self.dict['BNB/ETH'] = self.ticks['BNB/ETH']['bid']
        self.dict['ETH/BNB'] = 1 / self.dict['BNB/ETH']

        # BNB & BTC
        self.dict['BNB/BTC'] = self.ticks['BNB/BTC']['bid']
        self.dict['BTC/BNB'] = 1 / self.dict['BNB/BTC']

    def margin(self, ent, mid, tar):
        tar_price = self.ticks['%s/%s' % (tar, ent)]['bid']
        # tar_amount = (1 / tar_price)
        mid_price = self.ticks['%s/%s' % (tar, mid)]['bid']
        out_amount = mid_price * self.dict['%s/%s' % (mid, ent)] * (1 / tar_price)
        return out_amount - 1

    def get_leastquoteVolume_dict(self):
        black_list = ['SUSD', 'DAI', 'USDC', 'BUSD', 'PAX']
        bars = self.ticks
        qv = {}
        for symbol in bars.keys():
            if symbol[-5:] == "/USDT" and bars[symbol]['bid'] > 0 and symbol not in black_list:
                # print(symbol + ': %f' % bars[symbol]['bid'])
                qv[symbol] = bars[symbol]['quoteVolume']
        qv = sorted(qv.items(), key=lambda item: item[1])[:self.sums]
        return qv

    def get_target(self):
        qv = self.get_leastquoteVolume_dict()
        dict = {}
        for i in range(self.sums):
            tar = qv[i][0].split('/')[0]
            for ent in self.ent_list:
                if '%s/%s' % (tar, ent) in self.ticks:
                    if self.ticks['%s/%s' % (tar, ent)]['bid'] > 0:
                        if tar in dict:
                            dict[tar].append(ent)
                        else:
                            dict[tar] = [ent]
        return dict

    def trading_info(self, ent, mid, tar):
        margin_per = self.margin(ent, mid, tar) * 100
        if margin_per > self.poundage * 5:
            return '%s: %s/%s U本位盈利 %f' % (tar, ent, mid, margin_per - self.poundage * 5)
        elif margin_per > self.poundage * 3:
            return '%s: %s/%s 币本位盈利 %f' % (tar, ent, mid, margin_per - self.poundage * 3)
        else:
            return '%s: %s/%s 亏损' % (tar, ent, mid)

    def auto_info(self):
        dict = self.get_target()
        for tar in dict.keys():
            ent_list = dict[tar]
            if len(ent_list) > 1:
                for i in range(len(ent_list)):
                    for j in range(len(ent_list)):
                        if i != j:
                            print(self.trading_info(ent_list[i], ent_list[j], tar))


exchange = ccxt.binance(
    {
        'apiKey': config.BINANCE_API_KEY,
        'secret': config.BINANCE_SECRET_KEY
    }
)

# print(interest(exchange).margin('ETH', 'BNB', 'WAN'))
# print(interest(exchange).get_target())
interest(exchange).auto_info()
