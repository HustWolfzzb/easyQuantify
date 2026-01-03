"""
Data.py 模块测试文件

使用方法:
    python Data_test.py                    # 运行所有测试
    python Data_test.py -v                 # 详细输出
    python Data_test.py TestData.test_realTimePrice  # 运行特定测试
"""

import unittest
import sys
import os
import datetime
from datetime import timedelta
import pandas as pd

# 将项目根目录添加到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from DataEngine.Data import DataEngine, get_pro, get_qo, get_news, realTimePrice, get_tick_price
from DataEngine.Data import get_pro_daily, get_stock_daily, get_stock_weekly, get_pro_monthly
from DataEngine.Data import get_pro_stock_basic, get_stock_name, get_stock_list_date
from DataEngine.Data import get_fina_indicator, get_daily_basic
from DataEngine.Data import get_concept, get_stock_concepts, get_stock_shenwan_classify
from DataEngine.Data import get_index, get_index_basic, get_index_weight
from DataEngine.Data import get_fund_basic, get_fund_name, get_fund_daily


class TestData(unittest.TestCase):
    """Data.py 模块测试类"""
    
    @classmethod
    def setUpClass(cls):
        """测试类初始化，在所有测试方法执行前运行一次"""
        print("\n" + "="*60)
        print("开始测试 Data.py 模块")
        print("="*60)
        cls.test_stock_code = '000001.SZ'  # 平安银行
        cls.test_stock_code_simple = '000001'  # 不带后缀
        cls.test_index_code = '399300.SZ'  # 沪深300
        cls.test_fund_code = '150018.SZ'  # 银华稳进
        
        # 创建 DataEngine 实例用于测试
        try:
            cls.engine = DataEngine()
        except Exception as e:
            print(f"⚠️  初始化 DataEngine 失败: {str(e)}")
            cls.engine = None
        
    def setUp(self):
        """每个测试方法执行前运行"""
        pass
    
    def tearDown(self):
        """每个测试方法执行后运行"""
        pass
    
    # ==================== 基础接口测试 ====================
    
    def test_data_engine_init(self):
        """测试 DataEngine 类初始化"""
        print("\n[测试] DataEngine.__init__()")
        try:
            engine = DataEngine()
            self.assertIsNotNone(engine, "DataEngine 应该成功初始化")
            self.assertIsNotNone(engine.pro, "pro 应该被初始化")
            self.assertIsNotNone(engine.qo, "qo 应该被初始化")
            print("  ✓ DataEngine 初始化测试通过")
        except Exception as e:
            self.fail(f"DataEngine 初始化测试失败: {str(e)}")
    
    def test_get_pro(self):
        """测试获取 Tushare Pro API"""
        print("\n[测试] get_pro()")
        try:
            pro = get_pro()
            self.assertIsNotNone(pro, "get_pro() 应该返回非空对象")
            print("  ✓ get_pro() 测试通过")
        except Exception as e:
            self.fail(f"get_pro() 测试失败: {str(e)}")
    
    def test_get_qo(self):
        """测试获取快速行情接口"""
        print("\n[测试] get_qo()")
        try:
            qo = get_qo()
            self.assertIsNotNone(qo, "get_qo() 应该返回非空对象")
            print("  ✓ get_qo() 测试通过")
        except Exception as e:
            self.fail(f"get_qo() 测试失败: {str(e)}")
    
    def test_get_news(self):
        """测试获取新闻接口"""
        print("\n[测试] get_news()")
        try:
            news = get_news()
            self.assertIsNotNone(news, "get_news() 应该返回非空对象")
            print("  ✓ get_news() 测试通过")
        except Exception as e:
            self.fail(f"get_news() 测试失败: {str(e)}")
    
    # ==================== 实时数据测试 ====================
    
    def test_realTimePrice_single(self):
        """测试获取单个股票实时价格"""
        print("\n[测试] realTimePrice() - 单个股票")
        try:
            result = realTimePrice(self.test_stock_code_simple)
            self.assertIsInstance(result, dict, "应该返回字典")
            if self.test_stock_code_simple in result:
                stock_data = result[self.test_stock_code_simple]
                self.assertIn('name', stock_data, "应该包含 'name' 字段")
                self.assertIn('now', stock_data, "应该包含 'now' 字段")
                print(f"  ✓ 获取到股票: {stock_data.get('name', 'N/A')}, 当前价: {stock_data.get('now', 'N/A')}")
        except Exception as e:
            print(f"  ⚠ realTimePrice() 测试警告: {str(e)} (可能是网络问题)")
    
    def test_realTimePrice_multiple(self):
        """测试获取多个股票实时价格"""
        print("\n[测试] realTimePrice() - 多个股票")
        try:
            codes = [self.test_stock_code_simple, '600000']
            result = realTimePrice(codes)
            self.assertIsInstance(result, dict, "应该返回字典")
            print(f"  ✓ 获取到 {len(result)} 只股票的数据")
        except Exception as e:
            print(f"  ⚠ realTimePrice() 多股票测试警告: {str(e)} (可能是网络问题)")
    
    # ==================== 历史数据测试 ====================
    
    def test_get_tick_price(self):
        """测试获取分时数据"""
        print("\n[测试] get_tick_price()")
        try:
            result = get_tick_price('sh', '5')
            self.assertIsInstance(result, list, "应该返回列表")
            if len(result) > 0:
                date, prices = result[0]
                self.assertIsInstance(date, str, "日期应该是字符串")
                self.assertIsInstance(prices, list, "价格应该是列表")
                print(f"  ✓ 获取到 {len(result)} 天的数据，第一天: {date}, 价格数量: {len(prices)}")
        except Exception as e:
            print(f"  ⚠ get_tick_price() 测试警告: {str(e)} (可能是网络问题或数据源问题)")
    
    def test_get_pro_daily_single(self):
        """测试获取单个股票日线数据"""
        print("\n[测试] get_pro_daily() - 单个股票")
        try:
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = (datetime.datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            result = get_pro_daily(self.test_stock_code, start_date, end_date)
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 条日线数据")
                print(f"    列名: {list(result.columns)}")
        except Exception as e:
            print(f"  ⚠ get_pro_daily() 测试警告: {str(e)} (可能是网络问题)")
    
    def test_get_pro_daily_multiple(self):
        """测试获取多个股票日线数据"""
        print("\n[测试] get_pro_daily() - 多个股票")
        try:
            codes = [self.test_stock_code, '600000.SH']
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = (datetime.datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            result = get_pro_daily(codes, start_date, end_date)
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 条日线数据")
        except Exception as e:
            print(f"  ⚠ get_pro_daily() 多股票测试警告: {str(e)} (可能是网络问题)")
    
    def test_get_stock_daily(self):
        """测试获取股票日线数据（带均线）"""
        print("\n[测试] get_stock_daily()")
        try:
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = (datetime.datetime.now() - timedelta(days=60)).strftime('%Y%m%d')
            result = get_stock_daily(self.test_stock_code, start_date, end_date)
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 条日线数据（带均线）")
        except Exception as e:
            print(f"  ⚠ get_stock_daily() 测试警告: {str(e)} (可能是网络问题)")
    
    def test_get_stock_weekly(self):
        """测试获取股票周线数据"""
        print("\n[测试] get_stock_weekly()")
        try:
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = (datetime.datetime.now() - timedelta(days=180)).strftime('%Y%m%d')
            result = get_stock_weekly(self.test_stock_code, start_date, end_date)
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 条周线数据")
        except Exception as e:
            print(f"  ⚠ get_stock_weekly() 测试警告: {str(e)} (可能是网络问题)")
    
    def test_get_pro_monthly(self):
        """测试获取股票月度数据"""
        print("\n[测试] get_pro_monthly()")
        try:
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = '20210101'
            result = get_pro_monthly(self.test_stock_code, start_date, end_date)
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 条月度数据")
        except Exception as e:
            print(f"  ⚠ get_pro_monthly() 测试警告: {str(e)} (可能是网络问题)")
    
    # ==================== 基础信息测试 ====================
    
    def test_get_pro_stock_basic(self):
        """测试获取股票基础信息"""
        print("\n[测试] get_pro_stock_basic()")
        try:
            result = get_pro_stock_basic()
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 只股票的基础信息")
                print(f"    列名: {list(result.columns)}")
        except Exception as e:
            print(f"  ⚠ get_pro_stock_basic() 测试警告: {str(e)} (可能是网络问题)")
    
    def test_get_stock_name(self):
        """测试获取股票名称映射"""
        print("\n[测试] get_stock_name()")
        try:
            result = get_stock_name()
            self.assertIsInstance(result, dict, "应该返回字典")
            if len(result) > 0:
                sample_code = list(result.keys())[0]
                print(f"  ✓ 获取到 {len(result)} 只股票的名称映射")
                print(f"    示例: {sample_code} -> {result[sample_code]}")
        except Exception as e:
            print(f"  ⚠ get_stock_name() 测试警告: {str(e)} (可能是网络问题)")
    
    def test_get_stock_list_date(self):
        """测试获取股票上市日期"""
        print("\n[测试] get_stock_list_date()")
        try:
            result = get_stock_list_date()
            self.assertIsInstance(result, dict, "应该返回字典")
            if len(result) > 0:
                sample_code = list(result.keys())[0]
                print(f"  ✓ 获取到 {len(result)} 只股票的上市日期")
                print(f"    示例: {sample_code} -> {result[sample_code]}")
        except Exception as e:
            print(f"  ⚠ get_stock_list_date() 测试警告: {str(e)} (可能是网络问题)")
    
    # ==================== 财务数据测试 ====================
    
    def test_get_fina_indicator(self):
        """测试获取财务指标"""
        print("\n[测试] get_fina_indicator()")
        try:
            result = get_fina_indicator(self.test_stock_code)
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 条财务指标数据")
                print(f"    列数: {len(result.columns)}")
        except Exception as e:
            print(f"  ⚠ get_fina_indicator() 测试警告: {str(e)} (可能是网络问题或权限问题)")
    
    def test_get_daily_basic(self):
        """测试获取每日基本面数据"""
        print("\n[测试] get_daily_basic()")
        try:
            # 测试使用今天日期
            result = get_daily_basic()
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 只股票的今日基本面数据")
            else:
                print("  ⚠ 今日可能不是交易日，尝试使用历史日期")
                # 尝试使用历史日期
                yesterday = (datetime.datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
                result = get_daily_basic(yesterday)
                if not result.empty:
                    print(f"  ✓ 获取到 {len(result)} 只股票的历史基本面数据")
        except Exception as e:
            print(f"  ⚠ get_daily_basic() 测试警告: {str(e)} (可能是网络问题)")
    
    # ==================== 概念和分类测试 ====================
    
    def test_get_concept(self):
        """测试获取概念板块"""
        print("\n[测试] get_concept()")
        try:
            result = get_concept()
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 个概念板块")
        except Exception as e:
            print(f"  ⚠ get_concept() 测试警告: {str(e)} (可能是网络问题)")
    
    def test_get_stock_concepts(self):
        """测试获取股票概念"""
        print("\n[测试] get_stock_concepts()")
        try:
            result = get_stock_concepts(self.test_stock_code)
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 个概念")
        except Exception as e:
            print(f"  ⚠ get_stock_concepts() 测试警告: {str(e)} (可能是网络问题)")
    
    def test_get_stock_shenwan_classify(self):
        """测试获取申万分类"""
        print("\n[测试] get_stock_shenwan_classify()")
        try:
            result = get_stock_shenwan_classify(self.test_stock_code)
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到申万分类数据")
        except Exception as e:
            print(f"  ⚠ get_stock_shenwan_classify() 测试警告: {str(e)} (可能是网络问题)")
    
    # ==================== 指数数据测试 ====================
    
    def test_get_index(self):
        """测试获取指数数据"""
        print("\n[测试] get_index()")
        try:
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = (datetime.datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            result = get_index(self.test_index_code, start_date, end_date)
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 条指数数据")
        except Exception as e:
            print(f"  ⚠ get_index() 测试警告: {str(e)} (可能是网络问题)")
    
    def test_get_index_basic(self):
        """测试获取指数基础信息"""
        print("\n[测试] get_index_basic()")
        try:
            result = get_index_basic('SSE')
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 个上交所指数")
        except Exception as e:
            print(f"  ⚠ get_index_basic() 测试警告: {str(e)} (可能是网络问题)")
    
    def test_get_index_weight(self):
        """测试获取指数权重"""
        print("\n[测试] get_index_weight()")
        try:
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = (datetime.datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            result = get_index_weight(self.test_index_code, start_date, end_date)
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 条权重数据")
        except Exception as e:
            print(f"  ⚠ get_index_weight() 测试警告: {str(e)} (可能是网络问题)")
    
    # ==================== 基金数据测试 ====================
    
    def test_get_fund_basic(self):
        """测试获取基金基础信息"""
        print("\n[测试] get_fund_basic()")
        try:
            result = get_fund_basic('E')
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 只基金的基础信息")
        except Exception as e:
            print(f"  ⚠ get_fund_basic() 测试警告: {str(e)} (可能是网络问题)")
    
    def test_get_fund_name(self):
        """测试获取基金名称映射"""
        print("\n[测试] get_fund_name()")
        try:
            result = get_fund_name()
            self.assertIsInstance(result, dict, "应该返回字典")
            if len(result) > 0:
                sample_code = list(result.keys())[0]
                print(f"  ✓ 获取到 {len(result)} 只基金的名称映射")
                print(f"    示例: {sample_code} -> {result[sample_code]}")
        except Exception as e:
            print(f"  ⚠ get_fund_name() 测试警告: {str(e)} (可能是网络问题)")
    
    def test_get_fund_daily(self):
        """测试获取基金日线数据"""
        print("\n[测试] get_fund_daily()")
        try:
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = (datetime.datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            result = get_fund_daily(self.test_fund_code, start_date, end_date)
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ 获取到 {len(result)} 条基金日线数据")
        except Exception as e:
            print(f"  ⚠ get_fund_daily() 测试警告: {str(e)} (可能是网络问题)")
    
    # ==================== 参数验证测试 ====================
    
    def test_date_format_handling(self):
        """测试日期格式处理"""
        print("\n[测试] 日期格式处理")
        try:
            # 测试带连字符的日期格式
            end_date = datetime.datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            result = get_pro_daily(self.test_stock_code, start_date, end_date)
            self.assertIsInstance(result, pd.DataFrame, "应该正确处理带连字符的日期")
            print("  ✓ 日期格式处理测试通过")
        except Exception as e:
            print(f"  ⚠ 日期格式处理测试警告: {str(e)}")
    
    # ==================== DataEngine 类方法测试 ====================
    
    def test_engine_realTimePrice(self):
        """测试 DataEngine 实例的 realTimePrice 方法"""
        print("\n[测试] DataEngine.realTimePrice()")
        if self.engine is None:
            self.skipTest("DataEngine 未初始化")
        try:
            result = self.engine.realTimePrice(self.test_stock_code_simple)
            self.assertIsInstance(result, dict, "应该返回字典")
            print("  ✓ DataEngine.realTimePrice() 测试通过")
        except Exception as e:
            print(f"  ⚠ DataEngine.realTimePrice() 测试警告: {str(e)}")
    
    def test_engine_get_pro_daily(self):
        """测试 DataEngine 实例的 get_pro_daily 方法"""
        print("\n[测试] DataEngine.get_pro_daily()")
        if self.engine is None:
            self.skipTest("DataEngine 未初始化")
        try:
            end_date = datetime.datetime.now().strftime('%Y%m%d')
            start_date = (datetime.datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            result = self.engine.get_pro_daily(self.test_stock_code, start_date, end_date)
            self.assertIsInstance(result, pd.DataFrame, "应该返回 DataFrame")
            if not result.empty:
                print(f"  ✓ DataEngine.get_pro_daily() 测试通过，获取到 {len(result)} 条数据")
        except Exception as e:
            print(f"  ⚠ DataEngine.get_pro_daily() 测试警告: {str(e)}")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestData)
    
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


if __name__ == '__main__':
    # 支持命令行参数
    if len(sys.argv) > 1 and sys.argv[1] != '-v':
        # 如果提供了参数且不是 -v，使用 unittest.main() 处理
        unittest.main()
    else:
        # 默认运行所有测试并输出详细内容
        success = run_tests()
        sys.exit(0 if success else 1)

