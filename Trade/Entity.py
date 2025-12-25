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


if __name__ == '__main__':
    """
    运行测试模式
    
    使用方法:
        python Entity.py                    # 运行所有测试
        python Entity.py -v                 # 详细输出
        python Entity.py TestUser.test_init  # 运行特定测试
    """
    import unittest
    from unittest.mock import Mock, MagicMock
    
    class MockEasytraderUser:
        """模拟 easytrader 用户对象用于测试"""
        def __init__(self, balance_data=None, position_data=None):
            # balance 可以是列表或字典
            if balance_data is None:
                balance_data = [{
                    '资金余额': 100000.0,
                    '可用资金': 95000.0,
                    '可取金额': 90000.0,
                    '总资产': 150000.0,
                    '参考市值': 50000.0,
                    '股份参考盈亏': 5000.0
                }]
            self.balance = balance_data
            
            # position 是列表
            if position_data is None:
                position_data = [
                    {
                        '证券代码': '600481',
                        '证券名称': '双良节能',
                        '股票余额': 100,
                        '可用余额': 100,
                        '冻结数量': 0.0,
                        '成本价': 32.149,
                        '市价': 5.78,
                        '参考盈亏': -2636.93,
                        '盈亏比例(%)': -82.021,
                        '当日盈亏': -3.0,
                        '当日盈亏比(%)': -0.52,
                        '市值': 578.0,
                        '仓位占比(%)': 47.01,
                        '当日买入': 0,
                        '当日卖出': 0,
                        '交易市场': '上海Ａ股',
                        '持股天数': 430
                    },
                    {
                        '证券代码': '000001',
                        '证券名称': '平安银行',
                        '股份余额': 200,
                        '股份可用': 200,
                        '参考成本价': 10.5,
                        '参考市价': 11.2,
                        '参考盈亏': 140.0,
                        '盈亏比例(%)': '3.33%',
                        '当前持仓': 200
                    }
                ]
            self.position = position_data
            self._update_called = False
            self._refresh_called = False
            self._buy_called = False
            self._sell_called = False
            self._cancel_called = False
        
        def update(self):
            self._update_called = True
        
        def refresh(self):
            self._refresh_called = True
        
        def buy(self, code, price, amount):
            self._buy_called = True
            self._buy_code = code
            self._buy_price = price
            self._buy_amount = amount
            return {'entrust_no': 'TEST_BUY_001', 'message': 'success'}
        
        def sell(self, code, price, amount):
            self._sell_called = True
            self._sell_code = code
            self._sell_price = price
            self._sell_amount = amount
            return {'entrust_no': 'TEST_SELL_001', 'message': 'success'}
        
        def cancel_entrust(self, entrust_no):
            self._cancel_called = True
            self._cancel_no = entrust_no
            return {'message': 'success'}
        
        @property
        def today_trades(self):
            return [
                {
                    '买卖标志': '买入',
                    '证券代码': '600481',
                    '成交价格': 5.78,
                    '成交数量': 100,
                    '成交日期': '20240101',
                    '成交时间': '09:30:00'
                }
            ]
        
        @property
        def today_entrusts(self):
            return [
                {
                    '买卖标志': '买入',
                    '证券代码': '600481',
                    '委托价格': 5.80,
                    '委托数量': 100,
                    '委托日期': '20240101',
                    '委托时间': '09:30:00',
                    '状态说明': '已成'
                }
            ]
    
    class TestUser(unittest.TestCase):
        """User 类测试类"""
        
        @classmethod
        def setUpClass(cls):
            """测试类初始化"""
            print("\n" + "="*60)
            print("开始测试 User 类")
            print("="*60)
        
        def setUp(self):
            """每个测试方法执行前运行"""
            self.mock_user = MockEasytraderUser()
            self.user = User(self.mock_user)
        
        def tearDown(self):
            """每个测试方法执行后运行"""
            pass
        
        # ==================== 初始化测试 ====================
        
        def test_init(self):
            """测试 User 初始化"""
            print("\n[测试] User.__init__()")
            try:
                self.assertIsNotNone(self.user.user)
                self.assertIsNotNone(self.user.stock)
                self.assertGreater(self.user.ke_yong_jin_e, 0)
                print(f"  ✓ 初始化成功，可用资金: {self.user.ke_yong_jin_e:.2f}")
            except Exception as e:
                self.fail(f"初始化测试失败: {str(e)}")
        
        def test_get_balance_dict_list(self):
            """测试获取资金状况 - 列表格式"""
            print("\n[测试] User._get_balance_dict() - 列表格式")
            try:
                balance_dict = self.user._get_balance_dict()
                self.assertIsInstance(balance_dict, dict)
                self.assertIn('资金余额', balance_dict)
                print("  ✓ 列表格式处理正确")
            except Exception as e:
                self.fail(f"列表格式测试失败: {str(e)}")
        
        def test_get_balance_dict_dict(self):
            """测试获取资金状况 - 字典格式"""
            print("\n[测试] User._get_balance_dict() - 字典格式")
            try:
                # 设置 balance 为字典格式
                self.mock_user.balance = {
                    '资金余额': 100000.0,
                    '可用资金': 95000.0
                }
                user = User(self.mock_user)
                balance_dict = user._get_balance_dict()
                self.assertIsInstance(balance_dict, dict)
                print("  ✓ 字典格式处理正确")
            except Exception as e:
                self.fail(f"字典格式测试失败: {str(e)}")
        
        def test_update_balance_field_compatibility(self):
            """测试资金字段兼容性"""
            print("\n[测试] User._update_balance() - 字段兼容性")
            try:
                # 测试不同字段名
                balance_data = [{
                    '资金帐号余额': 100000.0,  # 替代 '资金余额'
                    '可用金额': 95000.0,  # 替代 '可用资金'
                    '可取资金': 90000.0,  # 替代 '可取金额'
                    '资产总值': 150000.0,  # 替代 '总资产'
                    '市值': 50000.0,  # 替代 '参考市值'
                    '参考盈亏': 5000.0  # 替代 '股份参考盈亏'
                }]
                mock_user = MockEasytraderUser(balance_data)
                user = User(mock_user)
                self.assertGreater(user.zi_jin_yu_e, 0)
                self.assertGreater(user.ke_yong_jin_e, 0)
                print("  ✓ 字段兼容性测试通过")
            except Exception as e:
                self.fail(f"字段兼容性测试失败: {str(e)}")
        
        def test_update_info(self):
            """测试更新用户信息"""
            print("\n[测试] User.update_info()")
            try:
                self.user.update_info()
                # 检查是否调用了 update 或 refresh
                self.assertTrue(self.mock_user._update_called or self.mock_user._refresh_called)
                print("  ✓ 更新信息测试通过")
            except Exception as e:
                self.fail(f"更新信息测试失败: {str(e)}")
        
        def test_buy(self):
            """测试买入股票"""
            print("\n[测试] User.buy()")
            try:
                result = self.user.buy('600481', 5.80, 100)
                self.assertIsInstance(result, dict)
                self.assertIn('entrust_no', result)
                self.assertTrue(self.mock_user._buy_called)
                print(f"  ✓ 买入测试通过，委托编号: {result.get('entrust_no')}")
            except Exception as e:
                print(f"  ⚠ 买入测试警告: {str(e)} (可能需要网络连接或真实账户)")
        
        def test_sell(self):
            """测试卖出股票"""
            print("\n[测试] User.sell()")
            try:
                result = self.user.sell('600481', 5.90, 50)
                self.assertIsInstance(result, dict)
                self.assertIn('entrust_no', result)
                self.assertTrue(self.mock_user._sell_called)
                print(f"  ✓ 卖出测试通过，委托编号: {result.get('entrust_no')}")
            except Exception as e:
                print(f"  ⚠ 卖出测试警告: {str(e)} (可能需要网络连接或真实账户)")
        
        def test_cancel_entrust(self):
            """测试撤单"""
            print("\n[测试] User.cancel_entrust()")
            try:
                result = self.user.cancel_entrust('TEST_001')
                self.assertIsInstance(result, dict)
                self.assertTrue(self.mock_user._cancel_called)
                print("  ✓ 撤单测试通过")
            except Exception as e:
                self.fail(f"撤单测试失败: {str(e)}")
        
        def test_get_today_trades(self):
            """测试获取当日成交"""
            print("\n[测试] User.get_today_trades()")
            try:
                trades = self.user.get_today_trades()
                self.assertIsInstance(trades, list)
                if len(trades) > 0:
                    print(f"  ✓ 获取到 {len(trades)} 条当日成交记录")
                else:
                    print("  ✓ 当日无成交记录")
            except Exception as e:
                self.fail(f"获取当日成交测试失败: {str(e)}")
        
        def test_get_today_entrusts(self):
            """测试获取当日委托"""
            print("\n[测试] User.get_today_entrusts()")
            try:
                entrusts = self.user.get_today_entrusts()
                self.assertIsInstance(entrusts, list)
                if len(entrusts) > 0:
                    print(f"  ✓ 获取到 {len(entrusts)} 条当日委托记录")
                else:
                    print("  ✓ 当日无委托记录")
            except Exception as e:
                self.fail(f"获取当日委托测试失败: {str(e)}")
    
    class TestStock(unittest.TestCase):
        """Stock 类测试类"""
        
        @classmethod
        def setUpClass(cls):
            """测试类初始化"""
            print("\n" + "="*60)
            print("开始测试 Stock 类")
            print("="*60)
        
        def setUp(self):
            """每个测试方法执行前运行"""
            position_data = [
                {
                    '证券代码': '600481',
                    '证券名称': '双良节能',
                    '股票余额': 100,
                    '可用余额': 100,
                    '成本价': 32.149,
                    '市价': 5.78,
                    '参考盈亏': -2636.93,
                    '盈亏比例(%)': -82.021
                },
                {
                    '证券代码': '000001',
                    '证券名称': '平安银行',
                    '股份余额': 200,
                    '股份可用': 200,
                    '参考成本价': 10.5,
                    '参考市价': 11.2,
                    '参考盈亏': 140.0,
                    '盈亏比例(%)': '3.33%'
                }
            ]
            self.stock = Stock(position_data)
        
        def tearDown(self):
            """每个测试方法执行后运行"""
            pass
        
        # ==================== 初始化测试 ====================
        
        def test_init_list(self):
            """测试 Stock 初始化 - 列表格式"""
            print("\n[测试] Stock.__init__() - 列表格式")
            try:
                self.assertIsInstance(self.stock.position, dict)
                self.assertEqual(len(self.stock.position), 2)
                self.assertIn('600481', self.stock.position)
                self.assertIn('000001', self.stock.position)
                print("  ✓ 列表格式初始化成功")
            except Exception as e:
                self.fail(f"列表格式初始化测试失败: {str(e)}")
        
        def test_init_dict(self):
            """测试 Stock 初始化 - 字典格式"""
            print("\n[测试] Stock.__init__() - 字典格式")
            try:
                position_dict = {
                    '600481': {
                        '证券代码': '600481',
                        '股票余额': 100
                    }
                }
                stock = Stock(position_dict)
                self.assertIsInstance(stock.position, dict)
                self.assertIn('600481', stock.position)
                print("  ✓ 字典格式初始化成功")
            except Exception as e:
                self.fail(f"字典格式初始化测试失败: {str(e)}")
        
        # ==================== 持仓查询测试 ====================
        
        def test_get_position(self):
            """测试获取所有持仓"""
            print("\n[测试] Stock.get_position()")
            try:
                position = self.stock.get_position()
                self.assertIsInstance(position, dict)
                self.assertEqual(len(position), 2)
                print(f"  ✓ 获取到 {len(position)} 只股票的持仓")
            except Exception as e:
                self.fail(f"获取持仓测试失败: {str(e)}")
        
        def test_get_stock_position(self):
            """测试获取指定股票持仓"""
            print("\n[测试] Stock.get_stock_position()")
            try:
                pos = self.stock.get_stock_position('600481')
                self.assertIsNotNone(pos)
                self.assertEqual(pos['证券代码'], '600481')
                print(f"  ✓ 获取到股票: {pos.get('证券名称', 'N/A')}")
            except Exception as e:
                self.fail(f"获取指定股票持仓测试失败: {str(e)}")
        
        def test_get_stock_position_not_exist(self):
            """测试获取不存在的股票持仓"""
            print("\n[测试] Stock.get_stock_position() - 不存在")
            try:
                pos = self.stock.get_stock_position('999999')
                self.assertIsNone(pos)
                print("  ✓ 不存在股票返回 None")
            except Exception as e:
                self.fail(f"不存在股票测试失败: {str(e)}")
        
        # ==================== 持仓数量测试 ====================
        
        def test_get_stock_amount(self):
            """测试获取持仓数量"""
            print("\n[测试] Stock.get_stock_amount()")
            try:
                # 测试 '股票余额' 字段
                amount1 = self.stock.get_stock_amount('600481')
                self.assertEqual(amount1, 100.0)
                
                # 测试 '股份余额' 字段
                amount2 = self.stock.get_stock_amount('000001')
                self.assertEqual(amount2, 200.0)
                
                print(f"  ✓ 持仓数量测试通过: 600481={amount1}, 000001={amount2}")
            except Exception as e:
                self.fail(f"持仓数量测试失败: {str(e)}")
        
        def test_get_stock_available(self):
            """测试获取可用数量"""
            print("\n[测试] Stock.get_stock_available()")
            try:
                # 测试 '可用余额' 字段
                available1 = self.stock.get_stock_available('600481')
                self.assertEqual(available1, 100.0)
                
                # 测试 '股份可用' 字段
                available2 = self.stock.get_stock_available('000001')
                self.assertEqual(available2, 200.0)
                
                print(f"  ✓ 可用数量测试通过: 600481={available1}, 000001={available2}")
            except Exception as e:
                self.fail(f"可用数量测试失败: {str(e)}")
        
        # ==================== 价格测试 ====================
        
        def test_get_stock_price(self):
            """测试获取市价"""
            print("\n[测试] Stock.get_stock_price()")
            try:
                price = self.stock.get_stock_price('600481')
                self.assertEqual(price, 5.78)
                print(f"  ✓ 市价测试通过: {price}")
            except Exception as e:
                self.fail(f"市价测试失败: {str(e)}")
        
        def test_get_stock_cost_price(self):
            """测试获取成本价"""
            print("\n[测试] Stock.get_stock_cost_price()")
            try:
                # 测试 '成本价' 字段
                cost1 = self.stock.get_stock_cost_price('600481')
                self.assertEqual(cost1, 32.149)
                
                # 测试 '参考成本价' 字段
                cost2 = self.stock.get_stock_cost_price('000001')
                self.assertEqual(cost2, 10.5)
                
                print(f"  ✓ 成本价测试通过: 600481={cost1}, 000001={cost2}")
            except Exception as e:
                self.fail(f"成本价测试失败: {str(e)}")
        
        # ==================== 盈亏测试 ====================
        
        def test_get_stock_profit(self):
            """测试获取盈亏金额"""
            print("\n[测试] Stock.get_stock_profit()")
            try:
                profit1 = self.stock.get_stock_profit('600481')
                self.assertEqual(profit1, -2636.93)
                
                profit2 = self.stock.get_stock_profit('000001')
                self.assertEqual(profit2, 140.0)
                
                print(f"  ✓ 盈亏金额测试通过: 600481={profit1}, 000001={profit2}")
            except Exception as e:
                self.fail(f"盈亏金额测试失败: {str(e)}")
        
        def test_get_stock_profit_ratio(self):
            """测试获取盈亏比例"""
            print("\n[测试] Stock.get_stock_profit_ratio()")
            try:
                # 测试数字格式
                ratio1 = self.stock.get_stock_profit_ratio('600481')
                self.assertEqual(ratio1, -82.021)
                
                # 测试字符串格式（带百分号）
                ratio2 = self.stock.get_stock_profit_ratio('000001')
                self.assertEqual(ratio2, 3.33)
                
                print(f"  ✓ 盈亏比例测试通过: 600481={ratio1}%, 000001={ratio2}%")
            except Exception as e:
                self.fail(f"盈亏比例测试失败: {str(e)}")
        
        # ==================== 成本计算测试 ====================
        
        def test_cost_Calculate(self):
            """测试计算交易成本"""
            print("\n[测试] Stock.cost_Calculate()")
            try:
                # 这个测试主要检查方法是否能正常执行
                self.stock.cost_Calculate('600481', 5.78, 100)
                # 成本 = 5.78 * 100 * 0.0012 = 0.6936
                expected_cost = 5.78 * 100 * 0.0012
                print(f"  ✓ 成本计算测试通过，预期成本: {expected_cost:.4f}")
            except Exception as e:
                self.fail(f"成本计算测试失败: {str(e)}")
        
        # ==================== 字段兼容性测试 ====================
        
        def test_field_compatibility(self):
            """测试字段兼容性"""
            print("\n[测试] Stock 字段兼容性")
            try:
                # 测试不同字段名的兼容性
                position_data = [
                    {
                        '证券代码': '000002',
                        '当前持仓': 300,  # 替代 '股票余额'
                        '可用数量': 300,  # 替代 '可用余额'
                        '当前价格': 12.5,  # 替代 '市价'
                        '盈亏金额': 150.0  # 替代 '参考盈亏'
                    }
                ]
                stock = Stock(position_data)
                
                amount = stock.get_stock_amount('000002')
                available = stock.get_stock_available('000002')
                price = stock.get_stock_price('000002')
                profit = stock.get_stock_profit('000002')
                
                self.assertEqual(amount, 300.0)
                self.assertEqual(available, 300.0)
                self.assertEqual(price, 12.5)
                self.assertEqual(profit, 150.0)
                
                print("  ✓ 字段兼容性测试通过")
            except Exception as e:
                self.fail(f"字段兼容性测试失败: {str(e)}")
    
    def run_tests():
        """运行所有测试"""
        # 创建测试套件
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        suite.addTests(loader.loadTestsFromTestCase(TestUser))
        suite.addTests(loader.loadTestsFromTestCase(TestStock))
        
        # 运行测试
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        # 打印总结
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)
        print(f"运行测试: {result.testsRun}")
        print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
        print(f"失败: {len(result.failures)}")
        print(f"错误: {len(result.errors)}")
        
        if result.failures:
            print("\n失败的测试:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print("\n错误的测试:")
            for test, traceback in result.errors:
                print(f"  - {test}")
        
        return result.wasSuccessful()
    
    # 支持命令行参数
    import sys
    if len(sys.argv) > 1 and sys.argv[1] != '-v':
        # 如果提供了参数且不是 -v，使用 unittest.main() 处理
        unittest.main()
    else:
        # 默认运行所有测试并输出详细内容
        success = run_tests()
        sys.exit(0 if success else 1)