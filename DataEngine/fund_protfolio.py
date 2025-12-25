import requests
import pandas as pd


def get_public_dates(code: str) -> list:
    '''
    获取基金持仓的公开日期
    -
    参数
    -
        code 基金代码
    返回
        公开持仓的日期列表
    '''
    headers = {
        'Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36 Edg/87.0.664.75',
        'Accept': '*/*',
        'Referer': 'http://fund.eastmoney.com/data/fundranking.html',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    }
    params = (
        ('FCODE', code),
        ('MobileKey', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('OSVersion', '14.3'),
        ('appVersion', '6.3.8'),
        ('cToken', 'a6hdhrfejje88ruaeduau1rdufna1e--.6'),
        ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('passportid', '3061335960830820'),
        ('plat', 'Iphone'),
        ('product', 'EFund'),
        ('serverVersion', '6.3.6'),
        ('version', '6.3.8'),
    )

    json_response = requests.get(
        'https://fundmobapi.eastmoney.com/FundMNewApi/FundMNIVInfoMultiple', headers=headers, params=params).json()
    if json_response['Datas'] is None:
        return []
    return json_response['Datas']


def get_inverst_postion(code: str, date=None) -> pd.DataFrame:
    '''
    根据基金代码跟日期获取基金持仓信息
    -
    参数

        code 基金代码
        date 公布日期 形如 '2020-09-31' 默认为 None，得到最新公布的数据
    返回

        持仓信息表格

    '''
    EastmoneyFundHeaders = {
        'User-Agent': 'EMProjJijin/6.2.8 (iPhone; iOS 13.6; Scale/2.00)',
        'GTOKEN': '98B423068C1F4DEF9842F82ADF08C5db',
        'clientInfo': 'ttjj-iPhone10,1-iOS-iOS13.6',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Host': 'fundmobapi.eastmoney.com',
        'Referer': 'https://mpservice.com/516939c37bdb4ba2b1138c50cf69a2e1/release/pages/FundHistoryNetWorth',
    }
    params = [
        ('FCODE', code),
        ('MobileKey', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('OSVersion', '14.3'),
        ('appType', 'ttjj'),
        ('appVersion', '6.2.8'),
        ('deviceid', '3EA024C2-7F22-408B-95E4-383D38160FB3'),
        ('plat', 'Iphone'),
        ('product', 'EFund'),
        ('serverVersion', '6.2.8'),
        ('version', '6.2.8'),
    ]
    if date is not None:
        params.append(('DATE', date))
    params = tuple(params)

    response = requests.get('https://fundmobapi.eastmoney.com/FundMNewApi/FundMNInverstPosition',
                            headers=EastmoneyFundHeaders, params=params)
    rows = []
    stocks = response.json()['Datas']['fundStocks']

    columns = {
        'GPDM': '股票代码',
        'GPJC': '股票简称',
        'JZBL': '持仓占比(%)',
        'PCTNVCHG': '较上期变化(%)',
    }
    if stocks is None:
        return pd.DataFrame(rows, columns=columns.values())

    df = pd.DataFrame(stocks)
    df = df[list(columns.keys())].rename(columns=columns)
    return df


if __name__ == "__main__":
    # 6 位基金代码
    code = '510050'
    # 创建 excel 文件
    # 获取基金公开持仓日期
    public_dates = get_public_dates(code)
    # 遍历全部公开日期，获取该日期公开的持仓信息
    if len(public_dates) > 1:
        date = public_dates[0]
        print(f'正在获取 {date} 的持仓信息......')
        df = get_inverst_postion(code, date=date)
        # 添加到 excel 表格中
        print(df)
        print(f'{date} 的持仓信息获取成功')
    # 保存 excel 文件
    else:
        print(f'{code} 没有公开持仓信息', public_dates)
