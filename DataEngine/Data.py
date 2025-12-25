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

# 将项目根目录添加到 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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

def get_index_weight(code='399300.SZ',start_date='20180901', end_date='20180930'):
    return pro.index_weight(index_code = code,start_date= start_date, end_date = end_date )

def get_stock_list_date(to_lower=True):
    def lower(c):
        return c.lower()
    stock_basic = get_pro_stock_basic(fields='ts_code,list_date')
    list_date = list(stock_basic['list_date'])
    if to_lower:
        codes = list(stock_basic['ts_code'].apply(lower))
    code_listdate = {codes[x]: list_date[x] for x in range(len(codes))}
    return code_listdate

def get_pro_stock_basic(fields='ts_code,symbol,name,area,industry,list_date'):
    return pro.stock_basic(exchange='', list_status='L', fields=fields)

def get_stock_name():
    def lower(c):
        return c.lower()
    stock_basic = get_pro_stock_basic(fields='ts_code,name')
    name = list(stock_basic['name'])
    codes = list(stock_basic['ts_code'])
    code_name = {codes[x]: name[x] for x in range(len(codes))}
    return code_name

def get_pro_daily(ts_code, start_date='2021-01-04', end_date= str(datetime.date.today().isoformat()).replace('-','')):
    if type(ts_code) == str:
        return pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    elif type(ts_code) == list:
        return pro.daily(ts_code=",".join(ts_code), start_date=start_date, end_date=end_date)
    else:
        return pro.daily()

def get_fund_basic(EO='E'):
    return pro.fund_basic(market=EO)

def get_fund_name():
    ss = get_fund_basic()
    code_name = {}
    for i in range(len(ss)):
        code = ss.loc[i,'ts_code']
        name = ss.loc[i,'name']
        code_name[code] = name
    return code_name


def get_fund_daily(ts_code='150018.SZ', start_date='20180101', end_date='20181029', ma=[5,10,20,50]):
    return ts.pro_bar(ts_code=ts_code,  asset = 'FD', ma=ma, start_date=start_date, end_date=end_date)

def get_stock_daily(ts_code='150018.SZ', start_date='20180101', end_date='20181029', ma=[5,10,20,50]):
    return ts.pro_bar(ts_code=ts_code,  asset = 'E', start_date=start_date, end_date=end_date, adj='qfq', ma=ma, freq='D')

def get_stock_weekly(ts_code='150018.SZ', start_date='20180101', end_date='20181029', ma=[5,10,20,50]):
    return ts.pro_bar(ts_code=ts_code,  asset = 'E', start_date=start_date, end_date=end_date, adj='qfq',  ma=ma, freq='W')


if __name__ == '__main__':
    # get_tick_price('sh')
    symbol = ["002164", "002517", "002457", "600723", "600918", "600720", "603187", "002271", "000759", "000735", "601933"]
    stock_name = ["宁波东力", "恺英网络", "青龙管业", "首商股份", "中泰证券", "祁连山", "海容冷链", "东方雨虹", "中百集团", "罗牛山", "永辉超市"]
    print("数据驱动引擎，获取数据的总接口")
    data = get_news()
    print(data)
