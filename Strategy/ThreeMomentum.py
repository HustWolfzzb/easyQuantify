from DataEngine.Data import  *
from Feature.feature import Momentum


def threeMonmentum(code='600900.SH',sdate='20150101',edate='20210101'):
    data = get_pro_daily(code,sdate,edate)
    data = data[::-1].reset_index()
    length = len(data['close'])
    flag = True
    MixMo = 0
    money = 100000
    stock = 1000
    gap = 10
    print("Start Position:%s, money:%s, stock:%s, Price:%s"%(money + stock * data['close'][25], money, stock,data['close'][25]))
    pos = [money + stock * data['close'][25]]
    for x in range(25,length):
        MO5 = Momentum(data,'close', x, 5)
        MO15 = Momentum(data,'close', x, 15)
        MO25 = Momentum(data,'close', x, 25)
        if flag and MixMo == 0:
            MixMo = round(MO5 + MO15 + MO25, 2)
            flag = False
        else:
            now3Mo = round(MO5 + MO15 + MO25, 2)
            if MixMo < gap and now3Mo >= gap:
                money = round(money + stock * data['close'][x], 2)
                stock = 0
                print(
                    "Sell Price:%s, Pre：%s, Now:%s,money:%s, stock:%s" % (data['close'][x], MixMo, now3Mo, money, stock))

            elif MixMo > gap and now3Mo <= gap:
                stock += money // (data['close'][x] * 100) * 100
                money = round(money - money // (data['close'][x] * 100) * data['close'][x] * 100, 2)
                print(
                    "Buy Price:%s, Pre：%s, Now:%s, money:%s, stock:%s" % (data['close'][x], MixMo, now3Mo, money, stock))
            pos.append(money + stock * data['close'][x])
            MixMo = now3Mo
    print("股价回撤率：%s, 资金回撤率：%s, 股价涨幅：%s, 资金涨幅：%s"%(
        round(1-min(data['close'])/data['close'][25],2),
        round(1-min(pos)/pos[0],2),
        round(data['close'][-1]/data['close'][25] - 1,2),
        round(pos[-1]/pos[0] - 1,2)))
    print("End Position:%s, money:%s, stock:%s, Price:%s"%(money + stock * data['close'][-1], money, stock, data['close'][-1]))
    # print("End Position:%s, money:%s, stock:%s"%(money + stock * data['close[]25], money, stock))


if __name__ == '__main__':
    threeMonmentum()