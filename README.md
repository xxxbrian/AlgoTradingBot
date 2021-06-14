# AlgoTradingBot

## 对原ccxt python库进行了修改，适配了okex模拟盘
```python
exchange=ccxt.okexpaper
```
经过验证，okex模拟盘数据存在问题，不适用于量化交易，仅保留`ccxt.okexpaper`,**不再使用**

## 三角套利算法 triangle.py

### interest().margin() 指定币种计算收益
```python
ent = 'ETH' # 入场币种
mid = 'BNB' # 中间币种
tar = 'WAN' # 目标币种

# margin -> int (单位入场币种最终收益)
interest(exchange).margin(ent,mid,tar)
```

### interest().get_target() 自动获取最低交易量前50的可用交易对
数据清洗：剔除bid为0的无效交易对以及稳定币交易对
```python
# get_target -> dict
interest(exchange).get_target()
```
返回字典示例：
```dict
{'DNT': ['BTC'], 'STPT': ['BTC'], 'DREP': ['BTC'], 'OG': ['BTC'], 'AUTO': ['BTC'], 'MDT': ['BTC'], 'ARDR': ['BTC'], 'ASR': ['BTC'], 'DCR': ['BTC'], 'DUSK': ['BTC'], 'NULS': ['BTC'], 'OM': ['BTC'], 'POLS': ['BTC', 'BNB'], 'AVA': ['BTC', 'BNB'], 'VITE': ['BTC'], 'WAN': ['ETH', 'BTC', 'BNB'], 'HIVE': ['BTC'], 'CFX': ['BTC'], 'CTXC': ['BTC'], 'MIR': ['BTC'], 'WING': ['BTC', 'BNB'], 'JUV': ['BTC'], 'ACM': ['BTC'], 'WTC': ['BTC', 'BNB'], 'TCT': ['BTC'], 'REP': ['ETH', 'BTC'], 'COCOS': ['BNB'], 'OXT': ['BTC'], 'BAR': ['BTC'], 'CTK': ['BTC', 'BNB'], 'MASK': ['BNB'], 'FIRO': ['ETH', 'BTC'], 'TRU': ['BTC'], 'BEAM': ['BTC'], 'FIO': ['BTC', 'BNB'], 'NMR': ['BTC', 'BNB'], 'KMD': ['ETH', 'BTC'], 'MBL': ['BNB']}
```

### interest().auto_info() 自动计算当前可盈利交易对（U本位&币本位）
```python
# auto_info -> None
interest(exchange).auto_info()
```
print结果示例：
```text
POLS: BTC/BNB 亏损
POLS: BNB/BTC U本位盈利 0.040950
AVA: BTC/BNB 亏损
AVA: BNB/BTC 亏损
WAN: ETH/BTC 亏损
WAN: ETH/BNB 亏损
WAN: BTC/ETH 亏损
WAN: BTC/BNB 亏损
WAN: BNB/ETH 亏损
WAN: BNB/BTC 币本位盈利 0.009902
WING: BTC/BNB 亏损
WING: BNB/BTC U本位盈利 0.278657
WTC: BTC/BNB 亏损
WTC: BNB/BTC U本位盈利 0.430472
REP: ETH/BTC U本位盈利 0.164277
REP: BTC/ETH 亏损
FIRO: ETH/BTC 亏损
FIRO: BTC/ETH 亏损
CTK: BTC/BNB 亏损
CTK: BNB/BTC 币本位盈利 0.024017
FIO: BTC/BNB 亏损
FIO: BNB/BTC 亏损
NMR: BTC/BNB 亏损
NMR: BNB/BTC 亏损
KMD: ETH/BTC 亏损
KMD: BTC/ETH 亏损
```

### interest().auto_info_schedule() 自动循环查询计算
由于ccxt`fetchTickers()`的特性，每次请求全部symbol被Binance等交易所api认为是上千次单独请求，导致在短时间内触发api请求次数限制 [#1](https://github.com/xxxbrian/AlgoTradingBot/issues/1)

`auto_info_schedule()`改用数据缓存和动态增量更新的方法，避免了触发请求限制

```python
sleep = 5 # 每5秒重新查询计算一次

# auto_info_schedule -> None
interest(exchange).auto_info_schedule(sleep) # sleep默认为2s
```

### interest().auto_run() 自动交易
通过`exchange.fetch_order`和`exchange.fetch_order_book`方法对交易对挂单进行查询，完成吃单。
```python
sleep = 5 # 每5秒重新查询计算一次

# auto_info_schedule -> None
interest(exchange).auto_run(sleep) # sleep默认为2s
```

### TODO
+ 加入挂单查询，对可盈利交易对进行分析
+ 短时间内多次查询，降低错误率
+ 根据利率和余额自动下单

## ~~布林带趋势算法 in_postion.py~~ （停止使用）
模拟盘胜率通过，实盘验证胜率过低，后证实okex提供的模拟盘数据存在问题。
