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


class DataEngine:
    """
    数据引擎类 - 提供股票、基金、指数等金融数据的获取接口
    
    该类封装了所有数据获取功能，包括：
    - 实时数据获取
    - 历史数据获取（分时、日线、周线、月线）
    - 基础信息获取
    - 财务数据获取
    - 概念和分类数据获取
    - 指数数据获取
    - 基金数据获取
    """
    
    def __init__(self, config_name: str = 'ts'):
        """
        初始化数据引擎
        
        Args:
            config_name: 配置名称，默认为 'ts'
        
    Raises:
        KeyError: 如果配置文件中没有 'api' 键
        Exception: 如果API初始化失败
    """
        self.config = Config(config_name).getInfo()
        self._init_apis()
        self.temp_data_dir = TEMP_DATA_DIR
    
    def _init_apis(self):
        """初始化API接口"""
        try:
            api_token = self.config['api']
            # 初始化 Tushare Pro API
            self.pro = ts.pro_api(api_token)
            ts.set_token(api_token)
            # 初始化快速行情接口
            self.qo = easyquotation.use('sina')
        except KeyError:
            raise KeyError("配置文件中缺少 'api' 键，请检查 Config/info.json")
        except Exception as e:
                raise Exception(f"初始化 API 失败: {str(e)}")
        
    # ==================== 基础接口方法 ====================
    
    def get_pro(self):
        """
        获取Tushare的pro权限账户
        
        Returns:
            ts.pro_api: Tushare Pro API 对象
        """
        return self.pro
    
    def get_qo(self):
        """
        获取快速行情接口对象
        
        Returns:
            easyquotation.quotation: 快速行情接口对象（使用新浪数据源）
        """
        return self.qo

    def get_news(self):
        """
        获取新闻接口对象
        
        Returns:
            pro.news: Tushare新闻接口对象
            
        Note:
            返回的是接口对象，需要调用具体方法获取新闻数据
        """
        return self.pro.news

    # ==================== 实时数据方法 ====================
    
    def realTimePrice(self, code: Union[str, List[str]]) -> Dict[str, Dict]:
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
            return self.qo.stocks(code)
        except Exception as e:
            raise Exception(f"获取实时价格失败: {str(e)}")

    # ==================== 历史数据方法 ====================

    def get_tick_price(self, code: str = 'sh', ktype: str = '5') -> List[Tuple[str, List[float]]]:
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

    def get_pro_daily(self, ts_code: Union[str, List[str], None] = None, 
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
                return self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            elif isinstance(ts_code, list):
                return self.pro.daily(ts_code=",".join(ts_code), start_date=start_date, end_date=end_date)
            else:
                return self.pro.daily()
        except Exception as e:
            raise Exception(f"获取日线数据失败: {str(e)}")
    
    def get_stock_daily(self, ts_code: str = '150018.SZ', start_date: str = '20180101', 
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
    
    def get_stock_weekly(self, ts_code: str = '150018.SZ', start_date: str = '20180101', 
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
    
    def get_pro_monthly(self, ts_code: str, start_date: str = None, end_date: str = None, 
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
            
            return self.pro.monthly(ts_code=ts_code, start_date=start_date, end_date=end_date, fields=fields)
        except Exception as e:
            raise Exception(f"获取月度数据失败: {str(e)}")

    # ==================== 基础信息方法 ====================
    
    def get_pro_stock_basic(self, fields: str = 'ts_code,symbol,name,area,industry,list_date') -> pd.DataFrame:
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
        cache_file = os.path.join(self.temp_data_dir, f'stock_basic_{fields_hash}.pkl')
        
        try:
            # 尝试从 API 获取数据
            df = self.pro.stock_basic(exchange='', list_status='L', fields=fields)
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
    
    def get_stock_name(self) -> Dict[str, str]:
        """
        获取所有股票代码到名称的映射
        
        Returns:
            dict: 股票代码到名称的映射字典
                格式: {'000001.SZ': '平安银行', '600000.SH': '浦发银行', ...}
        
        Raises:
            Exception: 如果获取数据失败
        """
        try:
            stock_basic = self.get_pro_stock_basic(fields='ts_code,name')
            name = list(stock_basic['name'])
            codes = list(stock_basic['ts_code'])
            code_name = {codes[x]: name[x] for x in range(len(codes))}
            return code_name
        except Exception as e:
            raise Exception(f"获取股票名称失败: {str(e)}")

    def get_stock_list_date(self, to_lower: bool = True) -> Dict[str, str]:
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
            
            stock_basic = self.get_pro_stock_basic(fields='ts_code,list_date')
            list_date = list(stock_basic['list_date'])
            
            if to_lower:
                codes = list(stock_basic['ts_code'].apply(lower))
            else:
                codes = list(stock_basic['ts_code'])
            
            code_listdate = {codes[x]: list_date[x] for x in range(len(codes))}
            return code_listdate
        except Exception as e:
            raise Exception(f"获取股票上市日期失败: {str(e)}")

    # ==================== 财务数据方法 ====================

    def get_fina_indicator(self, ts_code: str) -> pd.DataFrame:
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
            return self.pro.fina_indicator(ts_code=ts_code)
        except Exception as e:
            raise Exception(f"获取财务指标失败: {str(e)}")

    def get_daily_basic(self, date: str = '') -> pd.DataFrame:
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
            
                df = self.pro.daily_basic(ts_code='', trade_date=date,
                                fields='ts_code,trade_date,close,turnover_rate_f,volume_ratio,pe,pb,free_share,total_mv')
            return df
        except Exception as e:
            raise Exception(f"获取每日基本面数据失败: {str(e)}")

    # ==================== 概念和分类方法 ====================
    
    def get_concept(self) -> pd.DataFrame:
        """
        获取概念板块列表
    
        Returns:
                pd.DataFrame: 概念板块数据，包含概念代码、名称等信息
            
        Raises:
            Exception: 如果获取数据失败
        """
        try:
            return self.pro.concept()
        except Exception as e:
            raise Exception(f"获取概念板块失败: {str(e)}")

    def get_stock_concepts(self, code: str) -> pd.DataFrame:
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
                return self.pro.concept_detail(index_code=code, fields='ts_code,name')
            return self.pro.concept_detail(ts_code=code)
        except Exception as e:
                raise Exception(f"获取股票概念失败: {str(e)}")

    def get_stock_shenwan_classify(self, code: str) -> pd.DataFrame:
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
                return self.pro.index_member(id=code)
            else:
                return self.pro.index_member(ts_code=code)
        except Exception as e:
            raise Exception(f"获取申万分类失败: {str(e)}")

    # ==================== 指数数据方法 ====================
    
    def get_index(self, ts_code: str = '399300.SZ', start_date: str = '20180101', end_date: str = '20181010') -> pd.DataFrame:
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
            
            df = self.pro.index_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            return df
        except Exception as e:
            raise Exception(f"获取指数数据失败: {str(e)}")

    def get_index_basic(self, market: str = 'SSE') -> pd.DataFrame:
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
            return self.pro.index_basic(market=market)
        except Exception as e:
            raise Exception(f"获取指数基础信息失败: {str(e)}")

    def get_index_weight(self, code: str = '399300.SZ', start_date: str = '20180901', end_date: str = '20180930') -> pd.DataFrame:
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
            
            return self.pro.index_weight(index_code=code, start_date=start_date, end_date=end_date)
        except Exception as e:
            raise Exception(f"获取指数权重失败: {str(e)}")

    # ==================== 基金数据方法 ====================
    
    def get_fund_basic(self, EO: str = 'E') -> pd.DataFrame:
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
            return self.pro.fund_basic(market=EO)
        except Exception as e:
            raise Exception(f"获取基金基础信息失败: {str(e)}")

    def get_fund_name(self) -> Dict[str, str]:
        """
        获取所有基金代码到名称的映射
        
        Returns:
            dict: 基金代码到名称的映射字典
                格式: {'150018.SZ': '银华稳进', '150019.SZ': '银华锐进', ...}
                
        Raises:
            Exception: 如果获取数据失败
        """
        try:
            ss = self.get_fund_basic()
            code_name = {}
            for i in range(len(ss)):
                code = ss.loc[i, 'ts_code']
                name = ss.loc[i, 'name']
                code_name[code] = name
            return code_name
        except Exception as e:
            raise Exception(f"获取基金名称失败: {str(e)}")

    def get_fund_daily(self, ts_code: str = '150018.SZ', start_date: str = '20180101', 
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


# ==================== 向后兼容的模块级函数 ====================
# 为了保持向后兼容性，创建一个默认实例并提供模块级函数接口

_default_engine = None

def _get_default_engine():
    """获取默认的数据引擎实例（单例模式）"""
    global _default_engine
    if _default_engine is None:
        _default_engine = DataEngine()
    return _default_engine

# 提供模块级函数接口以保持向后兼容
def get_pro():
    """获取Tushare的pro权限账户（向后兼容函数）"""
    return _get_default_engine().get_pro()

def get_qo():
    """获取快速行情接口对象（向后兼容函数）"""
    return _get_default_engine().get_qo()

def get_news():
    """获取新闻接口对象（向后兼容函数）"""
    return _get_default_engine().get_news()

def realTimePrice(code: Union[str, List[str]]) -> Dict[str, Dict]:
    """获取股票实时价格信息（向后兼容函数）"""
    return _get_default_engine().realTimePrice(code)

def get_tick_price(code: str = 'sh', ktype: str = '5') -> List[Tuple[str, List[float]]]:
    """获取历史分时记录（向后兼容函数）"""
    return _get_default_engine().get_tick_price(code, ktype)

def get_concept() -> pd.DataFrame:
    """获取概念板块列表（向后兼容函数）"""
    return _get_default_engine().get_concept()

def get_pro_monthly(ts_code: str, start_date: str = None, end_date: str = None, 
                   fields: str = 'ts_code,trade_date,open,high,low,close,vol,amount') -> pd.DataFrame:
    """获取股票月度数据（向后兼容函数）"""
    return _get_default_engine().get_pro_monthly(ts_code, start_date, end_date, fields)

def get_stock_concepts(code: str) -> pd.DataFrame:
    """获取股票所属概念或概念包含的股票（向后兼容函数）"""
    return _get_default_engine().get_stock_concepts(code)

def get_stock_shenwan_classify(code: str) -> pd.DataFrame:
    """获取股票申万分类或分类包含的股票（向后兼容函数）"""
    return _get_default_engine().get_stock_shenwan_classify(code)

def get_fina_indicator(ts_code: str) -> pd.DataFrame:
    """获取股票的财务指标数据（向后兼容函数）"""
    return _get_default_engine().get_fina_indicator(ts_code)

def get_daily_basic(date: str = '') -> pd.DataFrame:
    """获取每日基本面数据（向后兼容函数）"""
    return _get_default_engine().get_daily_basic(date)

def get_index(ts_code: str = '399300.SZ', start_date: str = '20180101', end_date: str = '20181010') -> pd.DataFrame:
    """获取指数日线数据（向后兼容函数）"""
    return _get_default_engine().get_index(ts_code, start_date, end_date)

def get_index_basic(market: str = 'SSE') -> pd.DataFrame:
    """获取指数基础信息（向后兼容函数）"""
    return _get_default_engine().get_index_basic(market)

def get_index_weight(code: str = '399300.SZ', start_date: str = '20180901', end_date: str = '20180930') -> pd.DataFrame:
    """获取指数成分股权重（向后兼容函数）"""
    return _get_default_engine().get_index_weight(code, start_date, end_date)

def get_stock_list_date(to_lower: bool = True) -> Dict[str, str]:
    """获取所有股票的上市日期（向后兼容函数）"""
    return _get_default_engine().get_stock_list_date(to_lower)

def get_pro_stock_basic(fields: str = 'ts_code,symbol,name,area,industry,list_date') -> pd.DataFrame:
    """获取股票基础信息（向后兼容函数）"""
    return _get_default_engine().get_pro_stock_basic(fields)

def get_stock_name() -> Dict[str, str]:
    """获取所有股票代码到名称的映射（向后兼容函数）"""
    return _get_default_engine().get_stock_name()

def get_pro_daily(ts_code: Union[str, List[str], None] = None, 
                  start_date: str = '2021-01-04', 
                  end_date: str = None) -> pd.DataFrame:
    """获取股票日线数据（向后兼容函数）"""
    return _get_default_engine().get_pro_daily(ts_code, start_date, end_date)

def get_fund_basic(EO: str = 'E') -> pd.DataFrame:
    """获取基金基础信息（向后兼容函数）"""
    return _get_default_engine().get_fund_basic(EO)

def get_fund_name() -> Dict[str, str]:
    """获取所有基金代码到名称的映射（向后兼容函数）"""
    return _get_default_engine().get_fund_name()

def get_fund_daily(ts_code: str = '150018.SZ', start_date: str = '20180101', 
                   end_date: str = '20181029', ma: List[int] = [5, 10, 20, 50]) -> pd.DataFrame:
    """获取基金日线数据（向后兼容函数）"""
    return _get_default_engine().get_fund_daily(ts_code, start_date, end_date, ma)

def get_stock_daily(ts_code: str = '150018.SZ', start_date: str = '20180101', 
                    end_date: str = '20181029', ma: List[int] = [5, 10, 20, 50]) -> pd.DataFrame:
    """获取股票日线数据（前复权，带均线）（向后兼容函数）"""
    return _get_default_engine().get_stock_daily(ts_code, start_date, end_date, ma)

def get_stock_weekly(ts_code: str = '150018.SZ', start_date: str = '20180101', 
                     end_date: str = '20181029', ma: List[int] = [5, 10, 20, 50]) -> pd.DataFrame:
    """获取股票周线数据（前复权，带均线）（向后兼容函数）"""
    return _get_default_engine().get_stock_weekly(ts_code, start_date, end_date, ma)
