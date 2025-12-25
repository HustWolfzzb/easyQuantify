import easytrader
import time
import tushare as ts
import datetime


class User():
    """
    用户实体类，封装 easytrader 的用户对象
    适配不同客户端的返回格式差异
    """
    def __init__(self, user):
        """
        初始化用户对象
        
        Args:
            user: easytrader 的用户对象
        """
        self.user = user
        self._update_balance()
        self.stock = Stock(user.position)

    def _get_balance_dict(self):
        """
        获取资金状况字典，处理 balance 返回列表的情况
        
        Returns:
            dict: 资金状况字典
        """
        balance = self.user.balance
        # easytrader 返回的是列表，取第一个元素
        if isinstance(balance, list) and len(balance) > 0:
            return balance[0]
        elif isinstance(balance, dict):
            return balance
        else:
            return {}

    def _update_balance(self):
        """更新资金状况，兼容不同客户端的字段名"""
        balance_dict = self._get_balance_dict()
        
        # 资金余额 - 兼容多种字段名
        self.zi_jin_yu_e = balance_dict.get('资金余额') or balance_dict.get('资金帐号余额') or 0.0
        
        # 可用资金 - 兼容多种字段名
        self.ke_yong_jin_e = balance_dict.get('可用资金') or balance_dict.get('可用金额') or 0.0
        
        # 可取金额 - 兼容多种字段名
        self.ke_qu_jin_e = balance_dict.get('可取金额') or balance_dict.get('可取资金') or 0.0
        
        # 总资产 - 兼容多种字段名
        self.zong_zi_chan = balance_dict.get('总资产') or balance_dict.get('资产总值') or 0.0
        
        # 参考市值
        self.can_kao_shi_zhi = balance_dict.get('参考市值') or balance_dict.get('市值') or 0.0
        
        # 股份参考盈亏
        self.gu_fen_ying_kui = balance_dict.get('股份参考盈亏') or balance_dict.get('参考盈亏') or 0.0

    def update_info(self):
        """
        更新用户信息（资金和持仓）
        """
        # 某些客户端使用 update()，某些使用 refresh()
        if hasattr(self.user, 'update'):
            self.user.update()
        elif hasattr(self.user, 'refresh'):
            self.user.refresh()
        
        self._update_balance()
        self.stock = Stock(self.user.position)

    def buy(self, code, price, amount):
        """
        买入股票
        
        Args:
            code: 股票代码
            price: 买入价格
            amount: 买入数量
            
        Returns:
            dict: 委托结果，包含 entrust_no 或 message
        """
        # 价格调整逻辑：如果价格接近当前价，使用当前价
        try:
            data = ts.get_realtime_quotes(code)
            price_now = float(data.at[0, 'price'])
            if price < price_now and price / price_now > 0.995:
                price = price_now
            elif price > price_now:
                price = price_now
        except Exception as e:
            print(f"获取实时价格失败: {e}，使用指定价格")
        
        result = self.user.buy(code, price, amount)
        print(f"买入委托: {result}")
        
        # 更新信息
        if hasattr(self.user, 'update'):
            self.user.update()
        elif hasattr(self.user, 'refresh'):
            self.user.refresh()
        
        return result

    def sell(self, code, price, amount):
        """
        卖出股票
        
        Args:
            code: 股票代码
            price: 卖出价格
            amount: 卖出数量
            
        Returns:
            dict: 委托结果，包含 entrust_no 或 message
        """
        # 检查可用持仓
        position = self.stock.get_position().get(code)
        if position:
            # 兼容不同客户端的可用数量字段名
            available = position.get('可用余额') or position.get('股份可用') or position.get('可用数量') or 0
            if available < amount:
                amount = available
                print(f"可用数量不足，调整为: {amount}")
        
        # 价格调整逻辑
        try:
            data = ts.get_realtime_quotes(code)
            price_now = float(data.at[0, 'price'])
            if price < price_now and price / price_now > 0.995:
                price = price_now
            elif price > price_now:
                price = price_now
        except Exception as e:
            print(f"获取实时价格失败: {e}，使用指定价格")
        
        result = self.user.sell(code, price, amount)
        print(f"卖出委托: {result}")
        
        # 更新信息
        if hasattr(self.user, 'update'):
            self.user.update()
        elif hasattr(self.user, 'refresh'):
            self.user.refresh()
        
        return result

    def cancel_entrust(self, entrust_no):
        """
        撤单
        
        Args:
            entrust_no: 委托编号
            
        Returns:
            dict: 撤单结果
        """
        result = self.user.cancel_entrust(entrust_no)
        print(f"撤单结果: {result}")
        return result

    def get_today_trades(self):
        """
        获取当日成交
        
        Returns:
            list: 当日成交列表
        """
        return self.user.today_trades

    def get_today_entrusts(self):
        """
        获取当日委托
        
        Returns:
            list: 当日委托列表
        """
        return self.user.today_entrusts


class Stock():
    """
    股票持仓实体类，封装持仓信息
    适配不同客户端的返回格式差异
    """
    def __init__(self, position):
        """
        初始化持仓对象
        
        Args:
            position: easytrader 返回的持仓列表
        """
        self.position = {}
        # position 是列表，每个元素是一个持仓字典
        if isinstance(position, list):
            for pos in position:
                code = pos.get('证券代码')
                if code:
                    self.position[code] = pos
        elif isinstance(position, dict):
            # 如果已经是字典格式，直接使用
            self.position = position

    def _get_field(self, pos_dict, *field_names):
        """
        获取字段值，兼容多种字段名
        
        Args:
            pos_dict: 持仓字典
            field_names: 可能的字段名列表
            
        Returns:
            字段值，如果都不存在返回 None
        """
        for field_name in field_names:
            if field_name in pos_dict:
                return pos_dict[field_name]
        return None

    def get_position(self):
        """
        获取所有持仓
        
        Returns:
            dict: 以股票代码为键的持仓字典
        """
        return self.position

    def get_stock_position(self, code):
        """
        获取指定股票的持仓信息
        
        Args:
            code: 股票代码
            
        Returns:
            dict: 持仓信息，如果不存在返回 None
        """
        return self.position.get(code)

    def get_stock_amount(self, code):
        """
        获取指定股票的持仓数量
        
        Args:
            code: 股票代码
            
        Returns:
            float: 持仓数量，如果不存在返回 0
        """
        pos = self.position.get(code)
        if not pos:
            return 0
        
        # 兼容不同字段名：股票余额、股份余额、当前持仓
        amount = self._get_field(pos, '股票余额', '股份余额', '当前持仓', '持仓数量')
        return float(amount) if amount is not None else 0.0

    def get_stock_available(self, code):
        """
        获取指定股票的可用数量
        
        Args:
            code: 股票代码
            
        Returns:
            float: 可用数量，如果不存在返回 0
        """
        pos = self.position.get(code)
        if not pos:
            return 0
        
        # 兼容不同字段名：可用余额、股份可用、可用数量
        available = self._get_field(pos, '可用余额', '股份可用', '可用数量')
        return float(available) if available is not None else 0.0

    def get_stock_price(self, code):
        """
        获取指定股票的市价
        
        Args:
            code: 股票代码
            
        Returns:
            float: 市价，如果不存在返回 0
        """
        pos = self.position.get(code)
        if not pos:
            return 0
        
        # 兼容不同字段名：市价、参考市价、当前价格
        price = self._get_field(pos, '市价', '参考市价', '当前价格', '最新价')
        return float(price) if price is not None else 0.0

    def get_stock_cost_price(self, code):
        """
        获取指定股票的成本价
        
        Args:
            code: 股票代码
            
        Returns:
            float: 成本价，如果不存在返回 0
        """
        pos = self.position.get(code)
        if not pos:
            return 0
        
        # 兼容不同字段名：成本价、参考成本价
        cost_price = self._get_field(pos, '成本价', '参考成本价')
        return float(cost_price) if cost_price is not None else 0.0

    def get_stock_profit(self, code):
        """
        获取指定股票的盈亏
        
        Args:
            code: 股票代码
            
        Returns:
            float: 盈亏金额，如果不存在返回 0
        """
        pos = self.position.get(code)
        if not pos:
            return 0
        
        # 兼容不同字段名：参考盈亏、盈亏
        profit = self._get_field(pos, '参考盈亏', '盈亏', '盈亏金额')
        return float(profit) if profit is not None else 0.0

    def get_stock_profit_ratio(self, code):
        """
        获取指定股票的盈亏比例
        
        Args:
            code: 股票代码
            
        Returns:
            float: 盈亏比例（百分比），如果不存在返回 0
        """
        pos = self.position.get(code)
        if not pos:
            return 0
        
        # 兼容不同字段名：盈亏比例(%)、盈亏比例
        profit_ratio = self._get_field(pos, '盈亏比例(%)', '盈亏比例')
        if profit_ratio is not None:
            # 如果是字符串，去掉百分号
            if isinstance(profit_ratio, str):
                profit_ratio = profit_ratio.replace('%', '').strip()
            return float(profit_ratio)
        return 0.0

    def cost_Calculate(self, code, price, amount):
        """
        计算交易成本
        
        Args:
            code: 股票代码
            price: 成交价
            amount: 成交份额
        """
        cost = price * amount * 0.0012
        print("*" * 20)
        print(f"股票代码：{code}")
        print(f"成交价：{price}")
        print(f"成交份额：{amount}")
        print(f"交易成本：{cost}")
        print("*" * 20)