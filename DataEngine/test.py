import pandas as pd
import time
import os
import sys
if sys.platform == 'linux':
    from Data import *
else:
    from DataEngine.Data import *
sys.path.append('../')
pd.set_option('display.max_rows',500)
pd.set_option('display.max_columns',500)
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)
pd.set_option('display.width', 180) # 设置打印宽度(**重要**)
from Feature.feature import *

from multiprocessing import *
# data = get_pro_daily(ts_code='600900.SH', start_date='20150101', end_date='20211011')
import tushare as ts
ts.set_token('4b98f5087a086ac0e0d759ce67daeb8a2de2773e12553e3989b303dd')
data = ts.pro_bar(ts_code='000725.SZ', start_date='20140901', end_date='20211011', ma=[5, 20, 50], adj='qfq')
data = data[::-1].reset_index()

def test(data, amount=10000, d_gap=0.007, u_gap=0.015, mini_amount=1000):
    data = data[::-1].reset_index()
    money = 1000000 - data['open'][0] * amount
    # use_able = amount
    # start = data['open'][0]
    # init = data['open'][0]
    # all_price = []
    buy_record = [mini_amount]
    sell_record = [mini_amount]
    flag = True
    # print("初始资金%s" % (money + data['open'][0] * amount))
    sell_price = 0
    for x in range(len(data)):
        time = data['trade_date'][x]
        open = data['open'][x]
        close = data['close'][x]
        high = data['high'][x]
        low = data['low'][x]
        sell_out = False
        if high >= open * (1 + u_gap):
            sell_price = open * (1 + u_gap)
            # sell_times = int((high - buy_record[-1][0]) // (u_gap*open) )
            count = 0
            times = 0
            while sell_price < high:
                # print("BBB")

                times += 1
                if count < 100:
                    count += 1
                # for i in range(sell_times):
                if amount > buy_record[-1]:
                    sell_amount = buy_record[-1]
                    sell_price = round(open + count * u_gap * (1 + count / 10) * open, 2)
                    if sell_price > high:
                        break
                    money += sell_price * sell_amount
                    amount -= sell_amount
                    sell_record.append(sell_amount)
                    # print('S-P:%s, A:%s, ALL:%s 【sell_len:%s】' % (
                    #     round(sell_price, 2), sell_amount, amount, len(sell_record)))
                else:
                    # pass
                    # print("卖光了：%s,%s,%s" % (money + data['close'][x] * amount, round(sell_price, 2), amount))
                    break
            if len(buy_record) > times:
                buy_record = buy_record[:len(buy_record) - times]
            else:
                buy_record = buy_record[0:1]

        if low < open * (1 - d_gap):
            count = 0
            times = 0
            buy_price = open * (1 - d_gap)
            while buy_price > low:
                # print("AAA")
                times = 0
                if count < 100:
                    count += 1
                # for i in range(int((buy_record[-1][0] - low)//d_gap)):
                buy_price = round(open - count * d_gap * (1 + (count - 1) / 10) * open, 2)
                if buy_price < low:
                    break
                buy_amount = \
                    ((open - buy_price) // (d_gap * (1 + (count - 1)) * open) + 1) * mini_amount
                if buy_amount < mini_amount:
                    buy_amount = mini_amount
                if money - buy_price * buy_amount > 0:
                    buy_record.append(buy_amount)
                    money -= buy_price * buy_amount
                    amount += buy_amount
                    # print('Buy:P: %s, A:%s, ALL:%s  【buy_len:%s】' % (
                    #     buy_price, buy_amount, amount, len(buy_record)))
                else:
                    # pass
                    # print("没钱买了：%s,%s,%s" % (money, buy_price, amount))
                    break
                if len(sell_record) > times:
                    sell_record = sell_record[:len(sell_record) - times]
                else:
                    sell_record = sell_record[0:1]
    return  money + data['close'][-1] * amount
        # print("\n===========\n")
        # all_price.append(p)
        # print("Date:%s, Position:%s High:%s, Low：%s\n" % (time, money + data['close'][x] * amount, high, low))

def test_MA(data, ma1, ma2, way, rate, all_l, multi=True):
    money = 1000000
    amount = 0
    index = 0
    start = ''
    operate_price = 0

    for x in range(len(data)):
        if x < data['trade_date'].tolist().index('20150105'):
            continue

        time_date = data['trade_date'][x]
        open = data['open'][x]
        close = data['close'][x]
        high = data['high'][x]
        low = data['low'][x]
        #
        # MA5 = Average(data,'open', x, 5)
        # MA10 = Average(data,'open', x, 10)
        # MA20 = Average(data,'open', x, 20)
        # MA30 = Average(data,'open', x, 30)
        # MA50 = Average(data,'open', x, 50)
        if way=='MA':
            MA5 = Average(data,'open', x, ma1)
            MA50 = Average(data,'open', x, ma2)
        else:
            MA5 = Momentum(data, 'open', x, ma1)
            MA50 = Momentum(data, 'open', x, ma2)
            if MA50 == 0:
                continue
        if amount == 0:
            if MA5>MA50*rate:
                buy_price = open
                buy_amount = money // (open * 100) * 100
                if operate_price == 0 or buy_price < operate_price:
                    # operate_price = buy_price
                    money -= buy_price * buy_amount
                    amount = buy_amount
                    pos = round(money + data['close'][x] * amount, 2)
                    start = time_date
                    if not multi:
                        print('【%s】Buy: %s, P: %s, A:%s, ALL:%s ' % ( index, time_date,
                            buy_price, buy_amount, pos ))
                        # print("Date:%s, Position:%s High:%s, Low：%s\n" % (time_date, money + data['close'][x] * amount, high, low))

        else:
            if not (MA5>MA50*rate):
                sell_price = open
                sell_amount = amount
                if operate_price < sell_price:
                    # operate_price = sell_price
                    money += sell_price * sell_amount
                    amount = 0
                    if len(start) == 8 :
                        Timegap = (int(time_date[:4])-int(start[:4])) * 365 + (int(time_date[4:6]) - int(start[4:6]) ) * 30 + (int(time_date[6:8]) - int(start[6:8]))
                    else:
                        Timegap = 0
                    pos = round(money + data['close'][x] * amount, 2)
                    if not multi:
                        print('【%s】Sell:%s, P: %s, A:%s, ALL:%s Timegap %s\n' % (index, time_date,
                            round(sell_price, 2), sell_amount, pos, Timegap ))
                    index += 1
                        # print("Date:%s, Position:%s High:%s, Low：%s\n" % (time_date, money + data['close'][x] * amount, high, low))
    all_l[ money + data['close'].tolist()[-1] * amount] = (ma1, ma2, way, rate)

def test_Booling(data,  ma=20, all_l={}, multi=False):
    money = 1000000
    amount = 0
    index = 0
    start = ''
    operate_price = 0
    for x in range(len(data)):
        if x < data['trade_date'].tolist().index('20150105'):
            continue
        time_date = data['trade_date'][x]
        close = data['close'][x]
        signal = Bollingger_Band(data, 'close', x, ma)
        if amount == 0:
            if signal=='Buy' or signal=='Add':
                buy_price = close
                buy_amount = money // (close * 100 ) * 100
                if operate_price == 0 or buy_price < operate_price:
                    # operate_price = buy_price
                    money -= buy_price * buy_amount
                    amount = buy_amount
                    pos = round(money + data['close'][x] * amount, 2)
                    start = time_date
                    if not multi:
                        print('【%s】Buy: %s, P: %s, A:%s, ALL:%s ' % (index, time_date,
                                                                     buy_price, buy_amount, pos))
                        # print("Date:%s, Position:%s High:%s, Low：%s\n" % (time_date, money + data['close'][x] * amount, high, low))

        else:
            if signal=='Reduce' or signal=='Sell':
                sell_price = close
                sell_amount = amount
                if operate_price < sell_price:
                    # operate_price = sell_price
                    money += sell_price * sell_amount
                    amount = 0
                    if len(start) == 8:
                        Timegap = (int(time_date[:4]) - int(start[:4])) * 365 + (
                                    int(time_date[4:6]) - int(start[4:6])) * 30 + (
                                              int(time_date[6:8]) - int(start[6:8]))
                    else:
                        Timegap = 0
                    pos = round(money + data['close'][x] * amount, 2)
                    if not multi:
                        print('【%s】Sell:%s, P: %s, A:%s, ALL:%s Timegap %s\n' % (index, time_date,
                                                                                 round(sell_price, 2), sell_amount, pos,
                                                                                 Timegap))
                    index += 1
                    # print("Date:%s, Position:%s High:%s, Low：%s\n" % (time_date, money + data['close'][x] * amount, high, low))
    all_l[money + data['close'].tolist()[-1] * amount] = (ma)

def test_WUGUI1(data, rate_up=0.2, rate_dowm=0.03, min_amount=500, start_amount=10000, all_l={}, multi=False):
    operate_price = data.loc[data['trade_date'].tolist().index('20150105'), 'open']
    amount = start_amount
    money = 1000000 - amount * operate_price
    index = 0
    buy_index = 0
    start = ''
    pos = 0
    start_price = 0
    for x in range(len(data)):
        if x < data['trade_date'].tolist().index('20150105'):
            continue
        if start_price == 0:
            start_price = data['open'][x]
        time_date = data['trade_date'][x]
        open = data['open'][x]
        close = data['close'][x]
        high = data['high'][x]
        low = data['low'][x]
        if low < open * (1-rate_dowm):
            for i in range( int((open - low)//(open*rate_dowm) )):
                buy_price = open * (1 - rate_dowm * (1 + i) )
                buy_amount =  min_amount * (int((open - buy_price)//rate_dowm)) * int(pos//1000000)
                if money >  buy_amount * buy_price:
                    money -= buy_price * buy_amount
                    amount += buy_amount
                    pos = round(money + data['close'][x] * amount, 2)
                    if not multi:
                        print('【%s - Buy】： P: %s, A:%s, POSITION:%s ' % (buy_index,
                                                                     buy_price, buy_amount, pos))
                        # print("Date:%s, Position:%s High:%s, Low：%s\n" % (time_date, money + data['close'][x] * amount, high, low))
                    buy_index += 1
                else:
                    break
        if high > open * (1 + rate_up) and amount > 0:
            for i in range( int((high - open)//(rate_up*open) ) ):
                sell_price = open * (1 + rate_up * (1 + i))
                sell_amount = min_amount * (int((high - open)//rate_up))  * int(pos//1000000)
                if amount < sell_amount:
                    sell_amount = amount
                money += sell_price * sell_amount
                amount -= sell_amount
                pos = round(money + data['close'][x] * amount, 2)
                if not multi:
                    print('【%s - Sell】 : P: %s, A:%s, POSITION:%s' % (index,
                                                                             round(sell_price, 2), sell_amount, pos
                                                                             ))
                index += 1
        if not multi:
            print("Date:%s, Position:%s. Open:%s, High:%s, Low：%s, Close :%s\n" % (time_date, money + data['close'][x] * amount, open, high, low, open))
    all_l[pos] = (rate_up, rate_dowm, min_amount, start_price, start_amount)


def test_WUGUI(data, rate_up=20, rate_dowm=3, min_amount=500, all_l={}, multi=False):
    operate_price = data.loc[data['trade_date'].tolist().index('20150105'), 'open']
    amount = 10000
    money = 1000000 - amount * operate_price
    cost = operate_price
    index = 0
    start = ''
    pos = 0
    start_price = 0
    for x in range(len(data)):
        if x < data['trade_date'].tolist().index('20150105'):
            continue
        if start_price == 0:
            start_price = data['open'][x]
        time_date = data['trade_date'][x]
        open = data['open'][x]
        close = data['close'][x]
        high = data['high'][x]
        low = data['low'][x]
        if amount == 0:
            operate_price = open
        while low < operate_price * (1 - rate_dowm):
            buy_price = operate_price * (1 - rate_dowm)
            # buy_amount =  min_amount
            buy_amount = (amount // min_amount + 1) * min_amount
            if money >  buy_amount * buy_price:
                operate_price = buy_price
                money -= buy_price * buy_amount
                cost = (amount * cost + buy_price * buy_amount) /(amount + buy_amount)
                amount += buy_amount
                pos = round(money + data['close'][x] * amount, 2)
                start = time_date
                if not multi:
                    print('【%s】Buy: %s, P: %s, A:%s, ALL:%s ' % (index, time_date,
                                                                 buy_price, buy_amount, pos))
                    # print("Date:%s, Position:%s High:%s, Low：%s\n" % (time_date, money + data['close'][x] * amount, high, low))
            else:
                break
        if high > cost * (1 + rate_up) and amount!=0:
            sell_price = cost * (1 + rate_up)
            sell_amount = amount
            money += sell_price * sell_amount
            amount = 0
            if len(start) == 8:
                Timegap = (int(time_date[:4]) - int(start[:4])) * 365 + (
                            int(time_date[4:6]) - int(start[4:6])) * 30 + (
                                      int(time_date[6:8]) - int(start[6:8]))
            else:
                Timegap = 0
            pos = round(money + data['close'][x] * amount, 2)
            if not multi:
                print('【%s】Sell:%s, P: %s, A:%s, ALL:%s Timegap %s\n' % (index, time_date,
                                                                         round(sell_price, 2), sell_amount, pos,
                                                                         Timegap))
            index += 1
            # print("Date:%s, Position:%s High:%s, Low：%s\n" % (time_date, money + data['close'][x] * amount, high, low))
    all_l[pos] = (rate_up, rate_dowm, min_amount, start_price)

def test_JUNXIAN(data, Range_up=10, Range_Down=5, ma1=5, ma2=20, ma3= 50, all_l={}, multi=False):
    operate_price = data.loc[data['trade_date'].tolist().index('20150105'), 'open']
    amount = 0
    money = 1000000 - amount * operate_price
    index = 0
    start = ''
    pos = 0
    start_price = 0
    ma1_l = []
    for x in range(len(data)):
        if x < data['trade_date'].tolist().index('20150105'):
            ma1_l.append( Average(data,'open', x, ma1) -  Average(data,'open', x-1, ma1))
            continue
        ma1_l.append(Average(data, 'open', x, ma1) - Average(data, 'open', x - 1, ma1))
        if len(ma1_l)>Range_up:
            ma1_l=ma1_l[-Range_up:]
        MA1 = Average(data,'open', x, ma1)
        MA2 = Average(data,'open', x, ma2)
        MA3 = Average(data,'open', x, ma3)
        time_date = data['trade_date'][x]
        open = data['open'][x]
        close = data['close'][x]
        high = data['high'][x]
        low = data['low'][x]
        if amount == 0:
            # MA_L = np.array(ma1_l)
            if sum(ma1_l)>0 and MA2 < MA3 and MA1 < MA2:
                buy_price = close
                buy_amount = money // (close * 100) * 100
                if operate_price == 0 or buy_price < operate_price:
                    # operate_price = buy_price
                    money -= buy_price * buy_amount
                    amount = buy_amount
                    pos = round(money + data['close'][x] * amount, 2)
                    start = time_date
                    if not multi:
                        print('【%s】Buy: %s, P: %s, A:%s, ALL:%s ' % (index, time_date,
                                                                     buy_price, buy_amount, pos))
                        # print("Date:%s, Position:%s High:%s, Low：%s\n" % (time_date, money + data['close'][x] * amount, high, low))

        else:
            if sum(ma1_l[-Range_Down:0])<0  and MA1>MA2 and MA2>MA3:
                sell_price = close
                sell_amount = amount

                # operate_price = sell_price
                money += sell_price * sell_amount
                amount = 0
                if len(start) == 8:
                    Timegap = (int(time_date[:4]) - int(start[:4])) * 365 + (
                                int(time_date[4:6]) - int(start[4:6])) * 30 + (
                                          int(time_date[6:8]) - int(start[6:8]))
                else:
                    Timegap = 0
                pos = round(money + data['close'][x] * amount, 2)
                if not multi:
                    print('【%s】Sell:%s, P: %s, A:%s, ALL:%s Timegap %s\n' % (index, time_date,
                                                                             round(sell_price, 2), sell_amount, pos,
                                                                             Timegap))
                index += 1
                    # print("Date:%s, Position:%s High:%s, Low：%s\n" % (time_date, money + data['close'][x] * amount, high, low))
    all_l[pos] = (Range_up, Range_Down, ma1, ma2, ma3, start_price)


all_earn = [0,0,0]
amounts = []
d_gaps = []
u_gaps = []
min_amounts = []

# for i in range(3,30):
#     for j in range(5,100):
#         for k in ['ma','mo']:
#             if i >= j:
#                 continue
#             try:
#                 earn = test_MA(data,i,j,k)
#             except Exception as e:
#                 print(e)
#                 continue
#             print("MA1:%s,MA2:%s,Way:%s 收益率：%s"%(i,j,k,round((earn - 1000000)/1000000,4)*100))
#             all_earn.append(earn)
# print("MAX :%s"%max(all_earn))

# for i in range(-70,70):
#     for j in range(0,10):
#         s2 = len(all_earn)
#         for k in range(1,15):
#             for m in range(3,10):
#                 earn = test(data,10000+i*100, 0.01+ 0.001*j,0.01+k*0.001, 200+m*100)
#                 all_earn.append(earn)
#                 print("POS:%s, Amount:%s,D_gap:%s, U_gap:%s, min:%s"%(earn, 10000+i*100, 0.01+ 0.001*j,0.01+k*0.001, 200+m*100))
#             s3=len(all_earn)
#         s2 = len((all_earn))
#     s1 = len(all_earn)
# test(data)
# print(max(all_earn))
# etf = pd.read_csv('/Users/zhangzhaobo/PycharmProjects/Quantify/DataEngine/etf.txt')
# ts.set_token('4b98f5087a086ac0e0d759ce67daeb8a2de2773e12553e3989b303dd')
#
# for year in ['2020']:
#     all_profit = pd.DataFrame(index=range(0, len(etf)),
#                               columns=['代码', '名称', '钱', '股份', '入价', '出价', '入金', '出金', '股价波动', '利润率'])
#     for et in range(len(etf)):
#         try:
#             if float(etf.loc[et, '市价']) < 2.5 and float(etf.loc[et, '市价']) > 0.5:# and str(etf.loc[et,'名称']).find('券')!=-1 :
#                 code = str(etf.loc[et, '代码'])
#                 if code[0] == '5':
#                     code += '.SH'
#                 else:
#                     code += '.SZ'
#                 name = etf.loc[et, '名称'].replace('行情吧档案', '')
#             else:
#                 continue
#         except Exception as e:
#             # print(e)
#             continue
#
#         if code + year + '.txt' not in os.listdir('etf/'):
#             if len(year) == 4:
#                 sd = year + '0130'
#                 ed = str(int(year) + 1) + '0130'
#             else:
#                 sd = year
#                 ed = str(int(year[:4]) + 1) + '0130'
#             print("第%s个code:%s 需要我自己找？" % (et, code))
#             time.sleep(0.6)
#             try:
#                 df = ts.pro_bar(ts_code=code, asset = 'FD', start_date=sd, end_date=ed)
#             except Exception as e:
#                 time.sleep(60)
#                 df = ts.pro_bar(ts_code=code, asset='FD', start_date=sd,
#                                 end_date=ed)
#             if len(df) < 40:
#                 df.to_csv('etf/' + code + year + '.txt')
#                 print("太短了,以致于没得数据，记个名字随便应付下")
#                 continue
#             df.to_csv('etf/' + code + year + '.txt')
#         else:
#             df = pd.read_csv('etf/' + code + year + '.txt')
#             if len(df) < 40:
#                 continue
#         # print(df.head())
#         money = 40000
#         amount = 40000
#         today_data = df.loc[len(df)-1]
#         gap = round(today_data['pre_close'] * 1003, 3)
#         # print(gap)
#         open_ziben = money + amount * today_data['pre_close']
#         open_price = today_data['pre_close']
#         # print(
#         #     '%s | 初始余额：%s, 初始股份:%s, 入场价：%s, 总资本：%s' % (name, money, round(amount), round(today_data['close'],3), round(money + amount * today_data['close'])))
#         operate_num = [100,200,300,400,500,600,700,800,900,1000,1100,1200,1300,1400,1500,1600,1700,1800,1900,2000,1500,1600,1700,1800,1900,2000]
#         col = {id : name for id,name in  zip(list(df.columns), range(len(list(df.columns))))}
#         for s in range(len(df)-1,-1,-1):
#             ma5 = df.iloc[s-6:s-1, col['close'] ].sum() / 5
#             ma10 = df.iloc[s-11:s-1, col['close'] ].sum() / 10
#             # ma50 = df.iloc[i-51:i-1, col['close'] ].sum() / 50
#             today_data = df.loc[s]
#             buy_times = 0
#             sell_times = 0
#             try:
#                 if today_data['high'] >= today_data['pre_close'] + gap:
#                     for i in range(1, int((today_data['high'] - today_data['pre_close']) // gap)):
#                         if today_data['pre_close'] > ma10 and i > 1:
#                             if amount >= (operate_num[i] + 200):
#                                 money += (today_data['pre_close'] + i * gap) * (operate_num[i] + 200)
#                                 amount -= (operate_num[i] + 200)
#                         else:
#                             if amount >= (operate_num[i]):
#                                 money += (today_data['pre_close'] + i * gap) * (operate_num[i])
#                                 amount -= operate_num[i]
#                         sell_times += 1
#                 if today_data['low'] <= today_data['pre_close'] - gap:
#                     for i in range(1, int((today_data['pre_close'] - today_data['low']) // gap)):
#                         if today_data['pre_close'] < ma10 and i > 1:
#                             if money >= (today_data['pre_close'] - i * gap) * (operate_num[i] + 200):
#                                 money -= (today_data['pre_close'] - i * gap) * (operate_num[i] + 200)
#                                 amount += (operate_num[i] + 200)
#                         else:
#                             if money >= (today_data['pre_close'] - i * gap) * (operate_num[i]):
#                                 money -= (today_data['pre_close'] - i * gap) * (operate_num[i])
#                                 amount += operate_num[i]
#                         buy_times += 1
#                 # if today_data['high'] >= today_data['close'] + gap:
#                 #     for i in range(1, int((today_data['high'] - today_data['close']) // gap)):
#                 #         if money >= (today_data['high'] - i * gap) * (operate_num[i]):
#                 #             money -= (today_data['high'] - i * gap) * (operate_num[i])
#                 #             amount += (operate_num[i])
#                 #             buy_times += 1
#                 # if today_data['low'] <= today_data['close'] - gap:
#                 #     for i in range(1, int((today_data['close'] - today_data['low']) // gap)):
#                 #         if amount > (operate_num[i]):
#                 #             money += (today_data['low'] + i * gap) * (operate_num[i])
#                 #             amount -= (operate_num[i])
#                 #             sell_times += 1
#             except IndexError as e:
#                 # print("今日份涨跌幅:%s 过大，直接木了"%today_data['pct_chg'])
#                 pass
#             # print('「%s」 %s||买：%s,卖：%s, (%s)【%s->[%s, %s]->%s】 余额：%s, 股份:%s, 总金额：%s'%(len(df)-1-s, today_data['trade_date'], buy_times, sell_times,round(today_data['pre_close'],3), round(today_data['open'],3), round(today_data['low'], 3), round(today_data['high'], 3), round(today_data['close'], 3), round(money), round(amount), round(money + amount * today_data['close'])))
#         start_data = df.loc[len(df) - 1]
#         today_data = df.loc[0]
#         all_profit.loc[et] = [code, name, round(money), round(amount), round(open_price, 3), round(today_data['close'], 3), round(open_ziben, 3) , round(money + amount * today_data['close']) , round(today_data['close']/open_price - 1 , 3), round((money + amount * today_data['close']) / open_ziben - 1, 3)]
#         # if round((money + amount * today_data['close'])/open_ziben - 1,2) < 0.1:
#         #     continue
#     # print(all_profit)
#     print(all_profit[all_profit['钱']>0])
#     print("len of all profit:%s"%len(all_profit[all_profit['钱']>0]))
#         # print(
#         #     '%s|%s__|__结余余额：%s, 结余股份:%s, 价：%s/%s(%s), 钱：%s/%s, (利润率:%s)' % (code, name,
#         #     round(money), round(amount), round(open_price,3), round(today_data['close'],3), round(today_data['close']/open_price - 1 ,3), round(open_ziben, 3) ,round(money + amount * today_data['close']) , round((money + amount * today_data['close'])/open_ziben - 1,3)))


def multi_process():
    core_num = cpu_count()
    # core_num = 2
    print("THE CORE OF THIS MACHINE IS %s......"%core_num)
    manager = Manager()
    all_l = manager.dict()
    # lock = manager.Lock()
    p = Pool(processes=core_num)
    pool = []
    for i in range(1, 5):
        for j in range(1,5):
            for k in range(5,20):
                for l in range(10,30):
                    p.apply_async(test_WUGUI1, args=(data, i / 100, j / 100, k * 100, l*1000, all_l, True))

                #     for m in range(15,30):

    p.close()
    p.join()
    return all_l


if __name__ == '__main__':
    time_start = time.time()
    all_l = multi_process()
    print("MAX :%s"%max(all_l.keys()))
    print(all_l[max(all_l.keys())])
    # symbol = {}
    # test_WUGUI1(data, 0.03, 0.01, 500, 10000, symbol)
    # print(symbol)
    print("Time usage:%s"%(time.time() - time_start))
