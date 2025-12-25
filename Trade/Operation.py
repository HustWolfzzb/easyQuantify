from random import randint
import tushare as ts
from Strategy.ThreeMomentum import threeMonmentum
from datetime import datetime, time, date
from time import sleep
import easyquotation
from DataEngine.Data import get_pro_daily, get_pro_stock_basic


class Trader():
    """
    交易操作类，封装交易逻辑
    适配重构后的 Entity.User 和 Entity.Stock
    """
    def __init__(self, user, code, price, amount, type):
        """
        初始化交易对象
        
        Args:
            user: Entity.User 对象
            code: 股票代码
            price: 价格
            amount: 数量
            type: 交易类型 ('buy', 'sell', 'b', 's')
        """
        self.user = user
        self.code = code
        # 价格精度处理：5开头（基金）保留3位小数，其他保留2位
        if code and len(code) > 0 and code[0] == '5':
            self.price = round(price, 3)
        else:
            self.price = round(price, 2)

        # 数量处理：按手（100股）取整
        self.amount = int(amount // 100 * 100)
        
        # 交易类型验证
        if type in ['buy', 'sell', 'b', 's']:
            self.type = type
        else:
            print(f"委托类型不明: {type}")
            self.type = None
        
        self.entrust_no = None  # 委托编号

    def trade(self, code=None, price=None, amount=None, type=None, names={}):
        """
        执行交易
        
        Args:
            code: 股票代码（可选，默认使用初始化时的值）
            price: 价格（可选，默认使用初始化时的值）
            amount: 数量（可选，默认使用初始化时的值）
            type: 交易类型（可选，默认使用初始化时的值）
            names: 股票名称字典，用于错误提示
            
        Returns:
            str: 委托编号（entrust_no），如果失败返回 None
        """
        # 更新交易参数
        if code:
            self.code = code
        if price is not None:
            if self.code and len(self.code) > 0 and self.code[0] == '5':
                self.price = round(price, 3)
            else:
                self.price = round(price, 2)
        if amount is not None:
            self.amount = int(amount // 100 * 100)
        if type:
            if type in ['buy', 'sell', 'b', 's']:
                self.type = type
            else:
                print(f"委托类型不明: {type}")
                return None

        # 交易类型名称映射
        type2name = {
            'b': "购入股票",
            's': "卖出股票",
            'buy': "购入股票",
            'sell': "卖出股票"
        }

        # 参数验证
        if not self.code or self.price <= 0 or self.amount <= 0 or not self.type:
            print("数据不符合规范:")
            print(f"\t代码：{self.code}")
            print(f"\t价格：{self.price}")
            print(f"\t委托数量：{self.amount}")
            print(f"\t买卖类型：{self.type}")
            return None

        # 执行买入
        if self.type in ['buy', 'b']:
            return self._execute_buy(type2name.get(self.type, "购入股票"), names)
        
        # 执行卖出
        elif self.type in ['sell', 's']:
            return self._execute_sell(type2name.get(self.type, "卖出股票"), names)
        
        return None

    def _execute_buy(self, type_name, names={}):
        """
        执行买入操作
        
        Args:
            type_name: 交易类型名称
            names: 股票名称字典
            
        Returns:
            str: 委托编号，失败返回 None
        """
        try:
            # 检查可用资金
            available_cash = self.user.ke_yong_jin_e
            required_cash = self.price * self.amount
            if available_cash < required_cash:
                print(f"资金不足: 可用资金 {available_cash:.2f}，需要 {required_cash:.2f}")
                print(f"错误日志:\n-->\t代码：{self.code}\n-->\t价格：{self.price}\n-->\t委托数量：{self.amount}\n-->\t买卖类型：{type_name}")
                return None

            # 执行买入
            buy_record = self.user.buy(self.code, self.price, self.amount)
            
            # 提取委托编号
            self.entrust_no = buy_record.get('entrust_no') or buy_record.get('message')
            
            if self.entrust_no:
                print(f"{type_name} 成功，代码：{self.code}，价格：{self.price}，数量：{self.amount}，委托编号：{self.entrust_no}")
            else:
                print(f"{type_name} 提交成功，代码：{self.code}，价格：{self.price}，数量：{self.amount}")
                print(f"返回结果：{buy_record}")
            
            return self.entrust_no

        except KeyError as e:
            print(f"委托可能未成功，无法获取委托编号：{str(e)}")
            print(f"错误日志:\n-->\t代码：{self.code}\n-->\t价格：{self.price}\n-->\t委托数量：{self.amount}\n-->\t买卖类型：{type_name}")
            return None
        except Exception as e:
            error_msg = str(e)
            stock_name = names.get(self.code, '')
            print(f"买入失败：{error_msg}")
            if stock_name:
                print(f"股票名称：{stock_name}")
            print(f"错误日志:\n-->\t代码：{self.code}\n-->\t价格：{self.price}\n-->\t委托数量：{self.amount}\n-->\t买卖类型：{type_name}")
            return None

    def _execute_sell(self, type_name, names={}):
        """
        执行卖出操作
        
        Args:
            type_name: 交易类型名称
            names: 股票名称字典
            
        Returns:
            str: 委托编号，失败返回 None
        """
        try:
            # 检查可用持仓
            available_amount = self.user.stock.get_stock_available(self.code)
            if available_amount <= 0:
                print(f"无可用持仓: 代码 {self.code}，可用数量 {available_amount}")
                print(f"错误日志:\n-->\t代码：{self.code}\n-->\t价格：{self.price}\n-->\t委托数量：{self.amount}\n-->\t买卖类型：{type_name}")
                return None

            # 如果委托数量超过可用数量，调整为可用数量
            if self.amount > available_amount:
                print(f"可用数量不足，从 {self.amount} 调整为 {available_amount}")
                self.amount = int(available_amount // 100 * 100)  # 按手取整
                if self.amount <= 0:
                    print(f"调整后数量为 0，无法卖出")
                    return None

            # 执行卖出
            sell_record = self.user.sell(self.code, self.price, self.amount)
            
            # 提取委托编号
            self.entrust_no = sell_record.get('entrust_no') or sell_record.get('message')
            
            if self.entrust_no:
                print(f"{type_name} 成功，代码：{self.code}，价格：{self.price}，数量：{self.amount}，委托编号：{self.entrust_no}")
            else:
                print(f"{type_name} 提交成功，代码：{self.code}，价格：{self.price}，数量：{self.amount}")
                print(f"返回结果：{sell_record}")
            
            return self.entrust_no

        except KeyError as e:
            print(f"委托可能未成功，无法获取委托编号：{str(e)}")
            print(f"错误日志:\n-->\t代码：{self.code}\n-->\t价格：{self.price}\n-->\t委托数量：{self.amount}\n-->\t买卖类型：{type_name}")
            return None
        except Exception as e:
            error_msg = str(e)
            stock_name = names.get(self.code, '')
            print(f"卖出失败：{error_msg}")
            if stock_name:
                print(f"股票名称：{stock_name}")
            print(f"错误日志:\n-->\t代码：{self.code}\n-->\t价格：{self.price}\n-->\t委托数量：{self.amount}\n-->\t买卖类型：{type_name}")
            return None

    def cancel(self):
        """
        撤单
        
        Returns:
            dict: 撤单结果
        """
        if not self.entrust_no:
            print("没有委托编号，无法撤单")
            return None
        
        try:
            result = self.user.cancel_entrust(self.entrust_no)
            print(f"撤单成功，委托编号：{self.entrust_no}")
            return result
        except Exception as e:
            print(f"撤单失败：{str(e)}")
            return None


# 程序运行时间在白天8:30 到 15:30  晚上20:30 到 凌晨 2:30
MORNING_START = time(9, 30)
DAY_END = time(11, 30)

AFTERNOON_START = time(13, 00)
AFTERNOON_END = time(15, 00)

if __name__ == '__main__':
    stocks = get_pro_stock_basic()
    codes = [x for x in stocks['ts_code'] if x[0] != 3 and x[:2]!='68']
    names = [x for x in stocks['name']]
    for x in range(len(codes)):
        if names[x].find('ST') != -1:
            continue
        print("\n\n模拟%s 三重指标"%names[x])
        sleep(1)
        threeMonmentum(codes[x], '20160101', '20210310')


