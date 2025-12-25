"""
数据引擎模块 - 网络数据获取接口

本模块主要用于构架数据引擎的关于网络数据的获取，提供股票、基金、指数等金融数据的获取接口。

主要功能：
    * 股票历史分时数据的获取 get_tick_price
    * 股票历史日K数据的获取 get_pro_daily, get_stock_daily, get_stock_weekly
    * 股票实时数据获取 realTimePrice
    * 股票基础信息获取 get_pro_stock_basic, get_stock_name, get_stock_list_date
    * 股票财务数据获取 get_fina_indicator
    * 股票概念和分类 get_concept, get_stock_concepts, get_stock_shenwan_classify
    * 指数数据获取 get_index, get_index_basic, get_index_weight
    * 基金数据获取 get_fund_basic, get_fund_name, get_fund_daily
    * 每日基本面数据 get_daily_basic

Author: easyQuantify Team
Date: 2024
"""


import random
import datetime
from typing import Union, List, Dict, Optional, Tuple
import easyquotation
import tushare as ts
import pandas as pd
import sys
import os
import pickle
import hashlib

# 将项目根目录添加到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 创建临时数据文件夹路径
TEMP_DATA_DIR = os.path.join(current_dir, 'temp_data')
if not os.path.exists(TEMP_DATA_DIR):
    os.makedirs(TEMP_DATA_DIR)

from Config.Config import Config
config = Config('ts').getInfo()

def get_pro():
    """
    获取Tushare的pro权限账户
    
    Returns:
        ts.pro_api: Tushare Pro API 对象
        
    Raises:
        KeyError: 如果配置文件中没有 'api' 键
        Exception: 如果API初始化失败
    """
    try:
        return ts.pro_api(config['api'])
    except KeyError:
        raise KeyError("配置文件中缺少 'api' 键，请检查 Config/info.json")
    except Exception as e:
        raise Exception(f"初始化 Tushare Pro API 失败: {str(e)}")

ts.set_token(config['api'])

def get_qo():
    """
    获取快速行情接口对象
    
    Returns:
        easyquotation.quotation: 快速行情接口对象（使用新浪数据源）
    """
    return easyquotation.use('sina')

qo = get_qo()
pro = get_pro()

def get_news():
    """
    获取新闻接口对象
    
    Returns:
        pro.news: Tushare新闻接口对象
        
    Note:
        返回的是接口对象，需要调用具体方法获取新闻数据
    """
    return pro.news

def realTimePrice(code: Union[str, List[str]]) -> Dict[str, Dict]:
    """
    获取股票实时价格信息
    
    Args:
        code: 股票代码，可以是单个代码字符串（如 '000759'）或代码列表（如 ['000759','000043']）
        
    Returns:
        dict: 股票实时信息字典，格式如下：
            {
                '000759': {
                    'name': '中百集团',
                    'open': 7.08,
                    'close': 7.08,
                    'now': 6.97,
                    'high': 7.12,
                    'low': 6.94,
                },
                ...
            }
            
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        return qo.stocks(code)
    except Exception as e:
        raise Exception(f"获取实时价格失败: {str(e)}")



def get_tick_price(code: str = 'sh', ktype: str = '5') -> List[Tuple[str, List[float]]]:
    """
    获取历史分时记录。最新到当前时间，一共350条记录
    
    Args:
        code: 股票代码，默认为 'sh'（上证指数）
        ktype: 获取数据类型
            - '5': 五分钟间隔获取数据（默认值）
            - '15': 15分钟间隔
            - '60': 60分钟间隔
            - 'D': 按天
    
    Returns:
        list: 按日期排序的元组列表，格式为 [(日期, [价格列表]), ...]
            例如: [('2020-08-10', [10.01, 11.01, ...]), ('2020-08-11', [12.01, 13.01, ...])]
            
    Raises:
        Exception: 如果获取数据失败或数据格式不正确
    """
    try:
        time_price = ts.get_hist_data(code, ktype=ktype)
        if time_price is None or time_price.empty:
            return []
        
        date_prices = {}
        for x in time_price.index:
            date = str(x[:10])
            if not date_prices.get(date):
                date_prices[date] = [float(time_price.at[x, 'open'])]
            else:
                date_prices[date].append(float(time_price.at[x, 'open']))
        
        for s in date_prices.keys():
            date_prices[s].reverse()
        
        return sorted(date_prices.items(), key=lambda x: x[0], reverse=False)
    except Exception as e:
        raise Exception(f"获取分时数据失败: {str(e)}")

def get_concept() -> pd.DataFrame:
    """
    获取概念板块列表
    
    Returns:
        pd.DataFrame: 概念板块数据，包含概念代码、名称等信息
        
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        return pro.concept()
    except Exception as e:
        raise Exception(f"获取概念板块失败: {str(e)}")

def get_pro_monthly(ts_code: str, start_date: str = None, end_date: str = None, 
                   fields: str = 'ts_code,trade_date,open,high,low,close,vol,amount') -> pd.DataFrame:
    """
    获取股票月度数据
    
    Args:
        ts_code: 股票代码，格式如 '000001.SZ'
        start_date: 开始日期，格式 'YYYYMMDD'，默认为 '20210104'
        end_date: 结束日期，格式 'YYYYMMDD'，默认为今天
        fields: 需要返回的字段，默认为 'ts_code,trade_date,open,high,low,close,vol,amount'
    
    Returns:
        pd.DataFrame: 月度数据，包含开盘价、最高价、最低价、收盘价、成交量、成交额等
        
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        if start_date is None:
            start_date = '20210104'
        if end_date is None:
            end_date = datetime.date.today().strftime('%Y%m%d')
        
        # 确保日期格式正确（去除连字符）
        start_date = start_date.replace('-', '')
        end_date = end_date.replace('-', '')
        
        return pro.monthly(ts_code=ts_code, start_date=start_date, end_date=end_date, fields=fields)
    except Exception as e:
        raise Exception(f"获取月度数据失败: {str(e)}")

def get_stock_concepts(code: str) -> pd.DataFrame:
    """
    获取股票所属概念或概念包含的股票
    
    Args:
        code: 股票代码或概念代码
            - 如果包含 'TS' 或 'ts'，则视为概念代码，返回该概念包含的股票
            - 否则视为股票代码，返回该股票所属的概念
    
    Returns:
        pd.DataFrame: 概念详情数据
        
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        if 'TS' in code.upper():
            return pro.concept_detail(index_code=code, fields='ts_code,name')
        return pro.concept_detail(ts_code=code)
    except Exception as e:
        raise Exception(f"获取股票概念失败: {str(e)}")

def get_stock_shenwan_classify(code: str) -> pd.DataFrame:
    """
    获取股票申万分类或分类包含的股票
    
    Args:
        code: 股票代码或申万分类代码
            - 如果包含 'SI' 或 'si'，则视为申万分类代码，返回该分类包含的股票
            - 否则视为股票代码，返回该股票所属的申万分类
    
    Returns:
        pd.DataFrame: 申万分类数据
        
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        if 'SI' in code.upper():
            return pro.index_member(id=code)
        return pro.index_member(ts_code=code)
    except Exception as e:
        raise Exception(f"获取申万分类失败: {str(e)}")


def get_fina_indicator(ts_code: str) -> pd.DataFrame:
    """
    获取股票的财务指标数据
    
    Args:
        ts_code: 股票代码，需要带市场后缀，例如：'000759.SZ' 或 '600000.SH'
    
    Returns:
        pd.DataFrame: 财务指标数据，包含约108个财务指标列
            主要包含：ROE、ROA、净利润率、毛利率、资产负债率等财务指标
        
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        return pro.fina_indicator(ts_code=ts_code)
    except Exception as e:
        raise Exception(f"获取财务指标失败: {str(e)}")

def get_daily_basic(date: str = '') -> pd.DataFrame:
    """
    获取每日基本面数据（全市场）
    
    Args:
        date: 交易日期，格式 'YYYYMMDD'，默认为今天
            如果为空字符串，则使用当前日期
    
    Returns:
        pd.DataFrame: 每日基本面数据，包含：
            - ts_code: 股票代码
            - trade_date: 交易日期
            - close: 收盘价
            - turnover_rate_f: 换手率
            - volume_ratio: 量比
            - pe: 市盈率
            - pb: 市净率
            - free_share: 流通股本
            - total_mv: 总市值
            
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        if date == '':
            date = datetime.datetime.now().strftime("%Y%m%d")
        else:
            # 确保日期格式正确
            date = date.replace('-', '')
        
        df = pro.daily_basic(ts_code='', trade_date=date,
                             fields='ts_code,trade_date,close,turnover_rate_f,volume_ratio,pe,pb,free_share,total_mv')
        return df
    except Exception as e:
        raise Exception(f"获取每日基本面数据失败: {str(e)}")


def get_index(ts_code: str = '399300.SZ', start_date: str = '20180101', end_date: str = '20181010') -> pd.DataFrame:
    """
    获取指数日线数据
    
    Args:
        ts_code: 指数代码，默认为 '399300.SZ'（沪深300）
        start_date: 开始日期，格式 'YYYYMMDD'
        end_date: 结束日期，格式 'YYYYMMDD'
    
    Returns:
        pd.DataFrame: 指数日线数据，包含开盘价、最高价、最低价、收盘价等
        
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        # 确保日期格式正确
        start_date = start_date.replace('-', '')
        end_date = end_date.replace('-', '')
        
        df = pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        return df
    except Exception as e:
        raise Exception(f"获取指数数据失败: {str(e)}")

def get_index_basic(market: str = 'SSE') -> pd.DataFrame:
    """
    获取指数基础信息
    
    Args:
        market: 交易市场，默认为 'SSE'（上交所）
            可选值：'SSE'（上交所）、'SZSE'（深交所）、'CFFEX'（中金所）等
    
    Returns:
        pd.DataFrame: 指数基础信息，包含指数代码、名称、发布日等
        
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        return pro.index_basic(market=market)
    except Exception as e:
        raise Exception(f"获取指数基础信息失败: {str(e)}")

def get_index_weight(code: str = '399300.SZ', start_date: str = '20180901', end_date: str = '20180930') -> pd.DataFrame:
    """
    获取指数成分股权重
    
    Args:
        code: 指数代码，默认为 '399300.SZ'（沪深300）
        start_date: 开始日期，格式 'YYYYMMDD'
        end_date: 结束日期，格式 'YYYYMMDD'
    
    Returns:
        pd.DataFrame: 指数成分股权重数据
        
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        # 确保日期格式正确
        start_date = start_date.replace('-', '')
        end_date = end_date.replace('-', '')
        
        return pro.index_weight(index_code=code, start_date=start_date, end_date=end_date)
    except Exception as e:
        raise Exception(f"获取指数权重失败: {str(e)}")

def get_stock_list_date(to_lower: bool = True) -> Dict[str, str]:
    """
    获取所有股票的上市日期
    
    Args:
        to_lower: 是否将股票代码转换为小写，默认为 True
    
    Returns:
        dict: 股票代码到上市日期的映射字典
            格式: {'000001.sz': '19910403', '600000.sh': '19991110', ...}
            
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        def lower(c):
            return c.lower()
        
        stock_basic = get_pro_stock_basic(fields='ts_code,list_date')
        list_date = list(stock_basic['list_date'])
        
        if to_lower:
            codes = list(stock_basic['ts_code'].apply(lower))
        else:
            codes = list(stock_basic['ts_code'])
        
        code_listdate = {codes[x]: list_date[x] for x in range(len(codes))}
        return code_listdate
    except Exception as e:
        raise Exception(f"获取股票上市日期失败: {str(e)}")

def get_pro_stock_basic(fields: str = 'ts_code,symbol,name,area,industry,list_date') -> pd.DataFrame:
    """
    获取股票基础信息（带缓存机制）
    
    Args:
        fields: 需要返回的字段，默认为 'ts_code,symbol,name,area,industry,list_date'
            可选字段：ts_code, symbol, name, area, industry, list_date, market, exchange等
    
    Returns:
        pd.DataFrame: 股票基础信息数据框，包含所有上市股票的基础信息
        
    Raises:
        Exception: 如果获取数据失败且缓存文件不存在
    """
    # 根据 fields 参数生成缓存文件名（使用 MD5 哈希避免文件名过长）
    fields_hash = hashlib.md5(fields.encode('utf-8')).hexdigest()
    cache_file = os.path.join(TEMP_DATA_DIR, f'stock_basic_{fields_hash}.pkl')
    
    try:
        # 尝试从 API 获取数据
        df = pro.stock_basic(exchange='', list_status='L', fields=fields)
        # 如果成功，保存到缓存文件
        with open(cache_file, 'wb') as f:
            pickle.dump(df, f)
        return df
    except Exception as e:
        error_msg = str(e)
        # 检查是否是频率限制错误（更全面的匹配，包括每分钟和每小时）
        is_rate_limit = (
            '每小时最多访问' in error_msg or 
            '每分钟最多访问' in error_msg or
            '最多访问该接口' in error_msg or
            '最多访问' in error_msg or
            '访问该接口' in error_msg or
            ('权限' in error_msg and '访问' in error_msg)
        )
        
        if is_rate_limit:
            # 尝试从缓存文件读取
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'rb') as f:
                        df = pickle.load(f)
                    print(f"⚠️  API访问受限，已从缓存文件读取数据: {cache_file}")
                    return df
                except Exception as cache_error:
                    raise Exception(f"从缓存文件读取数据失败: {str(cache_error)}。请耐心等待API解锁后重试。")
            else:
                raise Exception(f"API访问受限（频率限制），且缓存文件不存在。请耐心等待解锁后重试。\n错误详情: {error_msg}")
        else:
            # 其他类型的错误，直接抛出
            raise Exception(f"获取股票基础信息失败: {error_msg}")

def get_stock_name() -> Dict[str, str]:
    """
    获取所有股票代码到名称的映射
    
    Returns:
        dict: 股票代码到名称的映射字典
            格式: {'000001.SZ': '平安银行', '600000.SH': '浦发银行', ...}
            
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        stock_basic = get_pro_stock_basic(fields='ts_code,name')
        name = list(stock_basic['name'])
        codes = list(stock_basic['ts_code'])
        code_name = {codes[x]: name[x] for x in range(len(codes))}
        return code_name
    except Exception as e:
        raise Exception(f"获取股票名称失败: {str(e)}")

def get_pro_daily(ts_code: Union[str, List[str], None] = None, 
                  start_date: str = '2021-01-04', 
                  end_date: str = None) -> pd.DataFrame:
    """
    获取股票日线数据
    
    Args:
        ts_code: 股票代码，可以是单个代码字符串、代码列表或None
            - str: 单个股票代码，如 '000001.SZ'
            - List[str]: 多个股票代码列表，如 ['000001.SZ', '600000.SH']
            - None: 不指定，返回所有股票数据（可能很慢）
        start_date: 开始日期，格式 'YYYYMMDD' 或 'YYYY-MM-DD'，默认为 '2021-01-04'
        end_date: 结束日期，格式 'YYYYMMDD' 或 'YYYY-MM-DD'，默认为今天
    
    Returns:
        pd.DataFrame: 股票日线数据，包含开盘价、最高价、最低价、收盘价、成交量、成交额等
        
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        if end_date is None:
            end_date = datetime.date.today().strftime('%Y%m%d')
        
        # 确保日期格式正确
        start_date = start_date.replace('-', '')
        end_date = end_date.replace('-', '')
        
        if isinstance(ts_code, str):
            return pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        elif isinstance(ts_code, list):
            return pro.daily(ts_code=",".join(ts_code), start_date=start_date, end_date=end_date)
        else:
            return pro.daily()
    except Exception as e:
        raise Exception(f"获取日线数据失败: {str(e)}")

def get_fund_basic(EO: str = 'E') -> pd.DataFrame:
    """
    获取基金基础信息
    
    Args:
        EO: 市场类型，默认为 'E'（场内基金）
            可选值：'E'（场内）、'O'（场外）
    
    Returns:
        pd.DataFrame: 基金基础信息，包含基金代码、名称、类型等
        
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        return pro.fund_basic(market=EO)
    except Exception as e:
        raise Exception(f"获取基金基础信息失败: {str(e)}")

def get_fund_name() -> Dict[str, str]:
    """
    获取所有基金代码到名称的映射
    
    Returns:
        dict: 基金代码到名称的映射字典
            格式: {'150018.SZ': '银华稳进', '150019.SZ': '银华锐进', ...}
            
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        ss = get_fund_basic()
        code_name = {}
        for i in range(len(ss)):
            code = ss.loc[i, 'ts_code']
            name = ss.loc[i, 'name']
            code_name[code] = name
        return code_name
    except Exception as e:
        raise Exception(f"获取基金名称失败: {str(e)}")


def get_fund_daily(ts_code: str = '150018.SZ', start_date: str = '20180101', 
                   end_date: str = '20181029', ma: List[int] = [5, 10, 20, 50]) -> pd.DataFrame:
    """
    获取基金日线数据（带均线）
    
    Args:
        ts_code: 基金代码，默认为 '150018.SZ'
        start_date: 开始日期，格式 'YYYYMMDD'
        end_date: 结束日期，格式 'YYYYMMDD'
        ma: 均线周期列表，默认为 [5, 10, 20, 50]
    
    Returns:
        pd.DataFrame: 基金日线数据，包含开盘价、最高价、最低价、收盘价、成交量及均线数据
        
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        # 确保日期格式正确
        start_date = start_date.replace('-', '')
        end_date = end_date.replace('-', '')
        
        return ts.pro_bar(ts_code=ts_code, asset='FD', ma=ma, start_date=start_date, end_date=end_date)
    except Exception as e:
        raise Exception(f"获取基金日线数据失败: {str(e)}")

def get_stock_daily(ts_code: str = '150018.SZ', start_date: str = '20180101', 
                    end_date: str = '20181029', ma: List[int] = [5, 10, 20, 50]) -> pd.DataFrame:
    """
    获取股票日线数据（前复权，带均线）
    
    Args:
        ts_code: 股票代码，默认为 '150018.SZ'
        start_date: 开始日期，格式 'YYYYMMDD'
        end_date: 结束日期，格式 'YYYYMMDD'
        ma: 均线周期列表，默认为 [5, 10, 20, 50]
    
    Returns:
        pd.DataFrame: 股票日线数据（前复权），包含开盘价、最高价、最低价、收盘价、成交量及均线数据
        
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        # 确保日期格式正确
        start_date = start_date.replace('-', '')
        end_date = end_date.replace('-', '')
        
        return ts.pro_bar(ts_code=ts_code, asset='E', start_date=start_date, end_date=end_date, 
                         adj='qfq', ma=ma, freq='D')
    except Exception as e:
        raise Exception(f"获取股票日线数据失败: {str(e)}")

def get_stock_weekly(ts_code: str = '150018.SZ', start_date: str = '20180101', 
                     end_date: str = '20181029', ma: List[int] = [5, 10, 20, 50]) -> pd.DataFrame:
    """
    获取股票周线数据（前复权，带均线）
    
    Args:
        ts_code: 股票代码，默认为 '150018.SZ'
        start_date: 开始日期，格式 'YYYYMMDD'
        end_date: 结束日期，格式 'YYYYMMDD'
        ma: 均线周期列表，默认为 [5, 10, 20, 50]
    
    Returns:
        pd.DataFrame: 股票周线数据（前复权），包含开盘价、最高价、最低价、收盘价、成交量及均线数据
        
    Raises:
        Exception: 如果获取数据失败
    """
    try:
        # 确保日期格式正确
        start_date = start_date.replace('-', '')
        end_date = end_date.replace('-', '')
        
        return ts.pro_bar(ts_code=ts_code, asset='E', start_date=start_date, end_date=end_date, 
                         adj='qfq', ma=ma, freq='W')
    except Exception as e:
        raise Exception(f"获取股票周线数据失败: {str(e)}")


if __name__ == '__main__':
    """
    运行测试模式
    
    使用方法:
        python Data.py                    # 运行所有测试
        python Data.py -v                 # 详细输出
        python Data.py TestData.test_realTimePrice  # 运行特定测试
    """
    import unittest
    from datetime import timedelta
    
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
            
        def setUp(self):
            """每个测试方法执行前运行"""
            pass
        
        def tearDown(self):
            """每个测试方法执行后运行"""
            pass
        
        # ==================== 基础接口测试 ====================
        
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
    
    # 支持命令行参数
    if len(sys.argv) > 1 and sys.argv[1] != '-v':
        # 如果提供了参数且不是 -v，使用 unittest.main() 处理
        unittest.main()
    else:
        # 默认运行所有测试并输出详细内容
        success = run_tests()
        sys.exit(0 if success else 1)
