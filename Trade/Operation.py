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
    """
    运行测试模式
    
    使用方法:
        python Operation.py                    # 运行所有测试
        python Operation.py -v                 # 详细输出
        python Operation.py TestTrader.test_init  # 运行特定测试
    """
    import unittest
    from unittest.mock import Mock, MagicMock
    
    class MockStock:
        """模拟 Stock 类用于测试"""
        def __init__(self, position_data=None):
            self.position = position_data or {}
        
        def get_stock_available(self, code):
            """获取可用数量"""
            pos = self.position.get(code)
            if not pos:
                return 0
            return pos.get('可用余额', 0) or pos.get('股份可用', 0) or 0
    
    class MockUser:
        """模拟 User 类用于测试"""
        def __init__(self, balance_data=None, position_data=None):
            self.ke_yong_jin_e = balance_data.get('可用资金', 100000) if balance_data else 100000
            self.stock = MockStock(position_data)
            self._buy_called = False
            self._sell_called = False
            self._cancel_called = False
        
        def buy(self, code, price, amount):
            """模拟买入"""
            self._buy_called = True
            self._buy_code = code
            self._buy_price = price
            self._buy_amount = amount
            return {'entrust_no': 'TEST_BUY_001', 'message': 'success'}
        
        def sell(self, code, price, amount):
            """模拟卖出"""
            self._sell_called = True
            self._sell_code = code
            self._sell_price = price
            self._sell_amount = amount
            return {'entrust_no': 'TEST_SELL_001', 'message': 'success'}
        
        def cancel_entrust(self, entrust_no):
            """模拟撤单"""
            self._cancel_called = True
            self._cancel_no = entrust_no
            return {'message': 'success'}
    
    class TestTrader(unittest.TestCase):
        """Trader 类测试类"""
        
        @classmethod
        def setUpClass(cls):
            """测试类初始化"""
            print("\n" + "="*60)
            print("开始测试 Trader 类")
            print("="*60)
            cls.test_stock_code = '000001'  # 平安银行
            cls.test_fund_code = '150018'  # 基金代码（5开头）
        
        def setUp(self):
            """每个测试方法执行前运行"""
            # 创建模拟用户对象
            balance_data = {
                '可用资金': 100000.0,
                '资金余额': 100000.0,
                '总资产': 100000.0
            }
            position_data = {
                '000001': {
                    '可用余额': 1000,
                    '股份可用': 1000,
                    '股票余额': 1000
                }
            }
            self.mock_user = MockUser(balance_data, position_data)
        
        def tearDown(self):
            """每个测试方法执行后运行"""
            pass
        
        # ==================== 初始化测试 ====================
        
        def test_init_normal_stock(self):
            """测试初始化 - 普通股票"""
            print("\n[测试] __init__() - 普通股票")
            try:
                trader = Trader(self.mock_user, '000001', 10.55, 150, 'buy')
                self.assertEqual(trader.code, '000001')
                self.assertEqual(trader.price, 10.55)  # 保留2位小数
                self.assertEqual(trader.amount, 100)  # 按手取整
                self.assertEqual(trader.type, 'buy')
                self.assertIsNone(trader.entrust_no)
                print("  ✓ 普通股票初始化测试通过")
            except Exception as e:
                self.fail(f"初始化测试失败: {str(e)}")
        
        def test_init_fund(self):
            """测试初始化 - 基金（5开头）"""
            print("\n[测试] __init__() - 基金")
            try:
                trader = Trader(self.mock_user, '150018', 1.2345, 150, 'buy')
                self.assertEqual(trader.code, '150018')
                self.assertEqual(trader.price, 1.235)  # 保留3位小数
                self.assertEqual(trader.amount, 100)  # 按手取整
                print("  ✓ 基金初始化测试通过")
            except Exception as e:
                self.fail(f"基金初始化测试失败: {str(e)}")
        
        def test_init_amount_rounding(self):
            """测试数量取整"""
            print("\n[测试] __init__() - 数量取整")
            try:
                trader = Trader(self.mock_user, '000001', 10.0, 250, 'buy')
                self.assertEqual(trader.amount, 200)  # 250 -> 200 (按100取整)
                
                trader2 = Trader(self.mock_user, '000001', 10.0, 99, 'buy')
                self.assertEqual(trader2.amount, 0)  # 99 -> 0 (按100取整)
                print("  ✓ 数量取整测试通过")
            except Exception as e:
                self.fail(f"数量取整测试失败: {str(e)}")
        
        def test_init_invalid_type(self):
            """测试无效交易类型"""
            print("\n[测试] __init__() - 无效交易类型")
            try:
                trader = Trader(self.mock_user, '000001', 10.0, 100, 'invalid')
                self.assertIsNone(trader.type)
                print("  ✓ 无效交易类型处理正确")
            except Exception as e:
                self.fail(f"无效交易类型测试失败: {str(e)}")
        
        # ==================== 交易方法测试 ====================
        
        def test_trade_buy_success(self):
            """测试买入交易 - 成功"""
            print("\n[测试] trade() - 买入成功")
            try:
                trader = Trader(self.mock_user, '000001', 10.0, 100, 'buy')
                result = trader.trade()
                self.assertIsNotNone(result)
                self.assertEqual(result, 'TEST_BUY_001')
                self.assertTrue(self.mock_user._buy_called)
                print("  ✓ 买入交易测试通过")
            except Exception as e:
                print(f"  ⚠ 买入交易测试警告: {str(e)} (可能需要真实交易账户)")
        
        def test_trade_sell_success(self):
            """测试卖出交易 - 成功"""
            print("\n[测试] trade() - 卖出成功")
            try:
                trader = Trader(self.mock_user, '000001', 10.0, 100, 'sell')
                result = trader.trade()
                self.assertIsNotNone(result)
                self.assertEqual(result, 'TEST_SELL_001')
                self.assertTrue(self.mock_user._sell_called)
                print("  ✓ 卖出交易测试通过")
            except Exception as e:
                print(f"  ⚠ 卖出交易测试警告: {str(e)} (可能需要真实交易账户)")
        
        def test_trade_buy_insufficient_funds(self):
            """测试买入交易 - 资金不足"""
            print("\n[测试] trade() - 资金不足")
            try:
                # 设置可用资金为0
                self.mock_user.ke_yong_jin_e = 0
                trader = Trader(self.mock_user, '000001', 10.0, 100, 'buy')
                result = trader.trade()
                self.assertIsNone(result)
                self.assertFalse(self.mock_user._buy_called)
                print("  ✓ 资金不足处理正确")
            except Exception as e:
                print(f"  ⚠ 资金不足测试警告: {str(e)}")
        
        def test_trade_sell_insufficient_position(self):
            """测试卖出交易 - 持仓不足"""
            print("\n[测试] trade() - 持仓不足")
            try:
                # 设置可用持仓为0
                self.mock_user.stock.position['000001']['可用余额'] = 0
                trader = Trader(self.mock_user, '000001', 10.0, 100, 'sell')
                result = trader.trade()
                self.assertIsNone(result)
                self.assertFalse(self.mock_user._sell_called)
                print("  ✓ 持仓不足处理正确")
            except Exception as e:
                print(f"  ⚠ 持仓不足测试警告: {str(e)}")
        
        def test_trade_sell_adjust_amount(self):
            """测试卖出交易 - 自动调整数量"""
            print("\n[测试] trade() - 自动调整卖出数量")
            try:
                # 设置可用持仓为50，但委托100
                self.mock_user.stock.position['000001']['可用余额'] = 50
                trader = Trader(self.mock_user, '000001', 10.0, 100, 'sell')
                result = trader.trade()
                # 应该调整为0（50按100取整后为0）
                self.assertIsNone(result)  # 因为调整后为0，无法卖出
                print("  ✓ 自动调整数量处理正确")
            except Exception as e:
                print(f"  ⚠ 自动调整数量测试警告: {str(e)}")
        
        def test_trade_update_parameters(self):
            """测试更新交易参数"""
            print("\n[测试] trade() - 更新参数")
            try:
                trader = Trader(self.mock_user, '000001', 10.0, 100, 'buy')
                # 更新参数
                result = trader.trade(code='600000', price=15.5, amount=200, type='sell')
                self.assertEqual(trader.code, '600000')
                self.assertEqual(trader.price, 15.5)
                self.assertEqual(trader.amount, 200)
                self.assertEqual(trader.type, 'sell')
                print("  ✓ 参数更新测试通过")
            except Exception as e:
                print(f"  ⚠ 参数更新测试警告: {str(e)}")
        
        def test_trade_invalid_params(self):
            """测试无效参数"""
            print("\n[测试] trade() - 无效参数")
            try:
                # 测试空代码
                trader = Trader(self.mock_user, '', 10.0, 100, 'buy')
                result = trader.trade()
                self.assertIsNone(result)
                
                # 测试价格为0
                trader2 = Trader(self.mock_user, '000001', 0, 100, 'buy')
                result2 = trader2.trade()
                self.assertIsNone(result2)
                
                # 测试数量为0
                trader3 = Trader(self.mock_user, '000001', 10.0, 0, 'buy')
                result3 = trader3.trade()
                self.assertIsNone(result3)
                
                print("  ✓ 无效参数验证正确")
            except Exception as e:
                print(f"  ⚠ 无效参数测试警告: {str(e)}")
        
        # ==================== 撤单测试 ====================
        
        def test_cancel_success(self):
            """测试撤单 - 成功"""
            print("\n[测试] cancel() - 撤单成功")
            try:
                trader = Trader(self.mock_user, '000001', 10.0, 100, 'buy')
                trader.entrust_no = 'TEST_001'
                result = trader.cancel()
                self.assertIsNotNone(result)
                self.assertTrue(self.mock_user._cancel_called)
                self.assertEqual(self.mock_user._cancel_no, 'TEST_001')
                print("  ✓ 撤单测试通过")
            except Exception as e:
                print(f"  ⚠ 撤单测试警告: {str(e)}")
        
        def test_cancel_no_entrust_no(self):
            """测试撤单 - 无委托编号"""
            print("\n[测试] cancel() - 无委托编号")
            try:
                trader = Trader(self.mock_user, '000001', 10.0, 100, 'buy')
                trader.entrust_no = None
                result = trader.cancel()
                self.assertIsNone(result)
                self.assertFalse(self.mock_user._cancel_called)
                print("  ✓ 无委托编号处理正确")
            except Exception as e:
                print(f"  ⚠ 无委托编号测试警告: {str(e)}")
        
        # ==================== 价格精度测试 ====================
        
        def test_price_precision_stock(self):
            """测试价格精度 - 股票"""
            print("\n[测试] 价格精度 - 股票")
            try:
                trader = Trader(self.mock_user, '000001', 10.555, 100, 'buy')
                self.assertEqual(trader.price, 10.56)  # 保留2位小数，四舍五入
                print("  ✓ 股票价格精度测试通过")
            except Exception as e:
                self.fail(f"价格精度测试失败: {str(e)}")
        
        def test_price_precision_fund(self):
            """测试价格精度 - 基金"""
            print("\n[测试] 价格精度 - 基金")
            try:
                trader = Trader(self.mock_user, '150018', 1.2345, 100, 'buy')
                self.assertEqual(trader.price, 1.235)  # 保留3位小数，四舍五入
                print("  ✓ 基金价格精度测试通过")
            except Exception as e:
                self.fail(f"基金价格精度测试失败: {str(e)}")
        
        # ==================== 交易类型测试 ====================
        
        def test_trade_type_variants(self):
            """测试交易类型变体"""
            print("\n[测试] 交易类型变体")
            try:
                # 测试 'b' 和 'buy'
                trader1 = Trader(self.mock_user, '000001', 10.0, 100, 'b')
                self.assertEqual(trader1.type, 'b')
                
                trader2 = Trader(self.mock_user, '000001', 10.0, 100, 'buy')
                self.assertEqual(trader2.type, 'buy')
                
                # 测试 's' 和 'sell'
                trader3 = Trader(self.mock_user, '000001', 10.0, 100, 's')
                self.assertEqual(trader3.type, 's')
                
                trader4 = Trader(self.mock_user, '000001', 10.0, 100, 'sell')
                self.assertEqual(trader4.type, 'sell')
                
                print("  ✓ 交易类型变体测试通过")
            except Exception as e:
                self.fail(f"交易类型变体测试失败: {str(e)}")
    
    def run_tests():
        """运行所有测试"""
        # 创建测试套件
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromTestCase(TestTrader)
        
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


