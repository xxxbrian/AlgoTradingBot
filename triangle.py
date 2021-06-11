# 重构版三角套利
# TODO 加入挂单查询，对可盈利交易对进行分析
# TODO 短时间内多次查询，降低错误率
# TODO 根据利率和余额自动下单
import time
import warnings

import schedule

import ccxt
import config as config

warnings.filterwarnings('ignore')

import logging
from logging import handlers


class Logger(object):
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'crit': logging.CRITICAL
    }  # 日志级别关系映射

    def __init__(self, filename, level='info', when='D', backCount=3,
                 fmt='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'):
        self.logger = logging.getLogger(filename)
        format_str = logging.Formatter(fmt)  # 设置日志格式
        self.logger.setLevel(self.level_relations.get(level))  # 设置日志级别
        sh = logging.StreamHandler()  # 往屏幕上输出
        sh.setFormatter(format_str)  # 设置屏幕上显示的格式
        th = handlers.TimedRotatingFileHandler(filename=filename, when=when, backupCount=backCount,
                                               encoding='utf-8')  # 往文件里写入 # 指定间隔时间自动生成文件的处理器
        # 实例化TimedRotatingFileHandler
        # interval是时间间隔，backupCount是备份文件的个数，如果超过这个个数，就会自动删除，when是间隔的时间单位，单位有以下几种：
        # S 秒
        # M 分
        # H 小时、
        # D 天、
        # W 每星期（interval==0时代表星期一）
        # midnight 每天凌晨
        th.setFormatter(format_str)  # 设置文件里写入的格式
        self.logger.addHandler(sh)  # 把对象加到logger里
        self.logger.addHandler(th)


class interest():
    def __init__(self, exchange):
        self.log = Logger('all.log', level='debug')
        self.markets = exchange.load_markets()
        self.ticks = exchange.fetch_tickers()
        self.ent_list = ['ETH', 'BTC', 'BNB']
        self.ent_mid_list = ['ETH/BTC', 'BNB/ETH', 'BNB/BTC']
        self.memdict = {}
        self.updata_list = []
        self.sums = 100
        self.all_sums = len(self.ticks)
        self.poundage = 0.075
        self.updata_EBB()

    def updata_EBB(self):
        self.dict = {}

        # ETH & BTC
        self.dict['ETH/BTC'] = self.ticks['ETH/BTC']['bid']
        self.dict['BTC/ETH'] = 1 / self.ticks['ETH/BTC']['ask']

        # BNB & ETH
        self.dict['BNB/ETH'] = self.ticks['BNB/ETH']['bid']
        self.dict['ETH/BNB'] = 1 / self.ticks['BNB/ETH']['ask']

        # BNB & BTC
        self.dict['BNB/BTC'] = self.ticks['BNB/BTC']['bid']
        self.dict['BTC/BNB'] = 1 / self.ticks['BNB/BTC']['ask']

    def updata_tickers(self):
        for updata in self.ent_mid_list:
            self.updata_list.append(updata)
        self.ticks = exchange.fetch_tickers(self.updata_list)
        self.updata_EBB()

    def margin(self, ent, mid, tar):
        tar_price = self.ticks['%s/%s' % (tar, ent)]['ask']
        # tar_amount = (1 / tar_price)
        mid_price = self.ticks['%s/%s' % (tar, mid)]['bid']
        out_amount = mid_price * self.dict['%s/%s' % (mid, ent)] * (1 / tar_price)
        return out_amount - 1

    def get_leastquoteVolume_dict(self):
        black_list = ['SUSD', 'DAI', 'USDC', 'BUSD', 'PAX']
        if len(self.ticks) <= self.all_sums * 0.9:
            self.ticks = exchange.fetch_tickers()
        bars = self.ticks
        qv = {}
        for symbol in bars.keys():
            if symbol[-5:] == "/USDT" and bars[symbol]['bid'] > 0 and symbol[:-5] not in black_list:
                # print(symbol + ': %f' % bars[symbol]['bid'])
                qv[symbol] = bars[symbol]['quoteVolume']
        qv = sorted(qv.items(), key=lambda item: item[1])[:self.sums]
        return qv

    def get_target(self, useselfdict=False):
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
        if useselfdict == True:
            self.memdict = dict
        return dict

    def trading_dict(self, ent, mid, tar):
        margin_per = self.margin(ent, mid, tar) * 100
        if margin_per > self.poundage * 5:
            return 'u', margin_per, margin_per - self.poundage * 3, margin_per - self.poundage * 5
        elif margin_per > self.poundage * 3:
            return 'b', margin_per, margin_per - self.poundage * 3, margin_per - self.poundage * 5
        else:
            return 'l', margin_per, margin_per - self.poundage * 3, margin_per - self.poundage * 5

    def trading_info(self, ent, mid, tar):
        margin_per = self.margin(ent, mid, tar) * 100
        if margin_per > self.poundage * 5:
            return '%s: %s/%s U本位盈利 %f' % (tar, ent, mid, margin_per - self.poundage * 5)
        elif margin_per > self.poundage * 3:
            return '%s: %s/%s 币本位盈利 %f' % (tar, ent, mid, margin_per - self.poundage * 3)
        else:
            return '%s: %s/%s 亏损 %f(币本）%f(无手续费）' % (tar, ent, mid, margin_per - self.poundage * 3, margin_per)

    def compute_all_info(self, dict):
        print(time.asctime(time.localtime(time.time())))
        try:
            self.updata_list = []
            for tar in dict.keys():
                ent_list = dict[tar]
                for ent in ent_list:
                    self.updata_list.append('%s/%s' % (tar, ent))
            self.updata_tickers()
            for tar in dict.keys():
                ent_list = dict[tar]
                if len(ent_list) > 1:
                    for i in range(len(ent_list)):
                        for j in range(len(ent_list)):
                            if i != j:
                                print(self.trading_info(ent_list[i], ent_list[j], tar))
        except Exception as e:
            print(e)
        else:
            print('')

    def compute_all(self, dict):
        transaction_list = []
        try:
            self.updata_list = []
            for tar in dict.keys():
                ent_list = dict[tar]
                for ent in ent_list:
                    self.updata_list.append('%s/%s' % (tar, ent))
            self.updata_tickers()
            for tar in dict.keys():
                ent_list = dict[tar]
                if len(ent_list) > 1:
                    for i in range(len(ent_list)):
                        for j in range(len(ent_list)):
                            if i != j:
                                standard, margin0, margin3, margin5 = self.trading_dict(ent_list[i], ent_list[j], tar)
                                transaction_list.append(
                                    {'standard': standard, 'tar': tar, 'ent': ent_list[i], 'mid': ent_list[j],
                                     'margin*0': margin0, 'margin*3': margin3, 'margin*5': margin5})
            transaction_list = sorted(transaction_list, key=lambda item: item['margin*0'], reverse=True)
            best = transaction_list[0]
            print(best)
            # 目前只做比本位交易
            if best['standard'] == 'u' or best['standard'] == 'b':
                self.order(best['ent'], best['mid'], best['tar'])
        except Exception as e:
            print(e)

    def order(self, ent, mid, tar, u_b='b'):
        # ent 2 tar
        ent2tar_orderbook = exchange.fetch_order_book('%s/%s' % (ent, tar))
        ent_amount = ent2tar_orderbook['bid'][0][0] * ent2tar_orderbook['bid'][0][1]
        myorder_ent2tar = self.b2b(ent, tar, min(ent_amount, exchange.fetch_balance()[ent]['free']))

        # tar 2 mid
        myorder_tar2mid = self.b2b(tar, mid, exchange.fetch_balance()[tar]['free'])

        # mid 2 ent
        myorder_mid2ent = self.b2b(mid, ent, myorder_tar2mid['amount'] * myorder_tar2mid['price'])

        if myorder_mid2ent['side'] == 'buy':
            out_amount = myorder_tar2mid['amount']
        else:  # sell
            out_amount = myorder_tar2mid['amount'] * myorder_tar2mid['price']

        return out_amount - ent_amount

    def b2b(self, inb, oub, inb_amount):
        if '%s/%s' % (inb, oub) in self.markets:
            order = exchange.create_order('%s/%s' % (inb, oub), 'market', 'sell', inb_amount, ...)
        elif '%s/%s' % (oub, inb) in self.markets:
            order = exchange.create_order('%s/%s' % (oub, inb), 'market', 'buy',
                                          inb_amount / self.ticks['%s/%s' % (oub, inb)]['ask'], ...)
        else:
            print('error')
            exit()
        while order['status'] != 'closed':
            time.sleep(0.15)
            order = exchange.fetch_order(order['id'])
        return order

    def auto_info(self):
        dict = self.get_target()
        self.compute_all_info(dict)

    def auto_info_schedule(self, sleep=2):
        self.get_target(True)
        schedule.every(1).hour.do(self.get_target, True)
        schedule.every(sleep).seconds.do(self.compute_all_info, self.memdict)
        while True:
            schedule.run_pending()

    def auto_run(self, sleep=2):
        self.get_target(True)
        schedule.every(1).hour.do(self.get_target, True)
        schedule.every(sleep).seconds.do(self.compute_all, self.memdict)
        while True:
            schedule.run_pending()


exchange = ccxt.binance(
    {
        'apiKey': config.BINANCE_API_KEY,
        'secret': config.BINANCE_SECRET_KEY
    }
)

# print(interest(exchange).margin('ETH', 'BNB', 'WAN'))
# print(interest(exchange).get_target())
# interest(exchange).auto_info()

# interest(exchange).auto_info_schedule()
interest(exchange).auto_run()
