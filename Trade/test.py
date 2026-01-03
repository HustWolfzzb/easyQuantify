"""
ETF 重新平衡测试脚本
功能：
1. 查询当前可用余额和持仓
2. 市价卖出所有当前持仓
3. 按照价格从低到高买入指定的 ETF 列表，直到资金用尽
"""

import time
import sys
import os
from typing import Dict, List, Optional, Any, Tuple

# 添加项目根目录到 Python 路径
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from Trade.TongHuaShunExecutor import TongHuaShunExecutor
from DataEngine.Data import DataEngine

# 目标 ETF 列表（不再需要 price 字段，将实时获取）
target_etfs = [
    {'name': '通信ETF', 'code': '159695'},
    {'name': '电池ETF', 'code': '159755'},
    {'name': '港股创新药ETF', 'code': '159567'},
    {'name': '机器人ETF', 'code': '159770'},
    {'name': '有色ETF', 'code': '512400'},
    {'name': '恒生科技指数ETF', 'code': '159742'},
    {'name': '创业板50ETF', 'code': '159949'},
    {'name': '光伏ETF', 'code': '515790'},
    {'name': '人工智能ETF', 'code': '159819'},
    {'name': '中韩芯片', 'code': '513310'}
]


def parse_float(value: Any) -> float:
    """
    将字符串或数字转换为浮点数
    
    Args:
        value: 要转换的值
        
    Returns:
        浮点数，如果转换失败返回 0.0
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # 移除可能的逗号、空格等
        value = value.replace(',', '').replace(' ', '').strip()
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def parse_int(value: Any) -> int:
    """
    将字符串或数字转换为整数
    
    Args:
        value: 要转换的值
        
    Returns:
        整数，如果转换失败返回 0
    """
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        # 移除可能的逗号、空格等
        value = value.replace(',', '').replace(' ', '').strip()
        try:
            return int(float(value))  # 先转 float 再转 int，处理 "100.0" 这种情况
        except ValueError:
            return 0
    return 0


def get_current_position(executor: TongHuaShunExecutor, data_engine: DataEngine) -> Tuple[float, List[Dict[str, Any]]]:
    """
    获取当前可用余额和持仓列表（使用实时价格接口）
    
    Args:
        executor: TongHuaShunExecutor 实例
        data_engine: DataEngine 实例，用于获取实时价格
        
    Returns:
        (可用余额, 持仓列表)
        持仓列表格式: [{'code': '股票代码', 'name': '股票名称', 'quantity': 数量, 'current_price': 当前价}, ...]
    """
    print("\n" + "="*60)
    print("步骤1: 查询当前资产和持仓")
    print("="*60)
    
    asset_data = executor.press_f4_query(use_vlm=True)
    
    if not asset_data:
        print("❌ 无法获取资产数据")
        return 0.0, []
    
    # 解析可用余额
    available_cash = parse_float(asset_data.get('available_cash', 0))
    print(f"\n✓ 可用余额: {available_cash:.2f} 元")
    
    # 解析持仓列表
    stocks = asset_data.get('stocks', [])
    positions = []
    
    if stocks:
        print(f"\n✓ 当前持仓 (共 {len(stocks)} 只):")
        
        # 批量获取所有持仓的实时价格
        codes = []
        for stock in stocks:
            code = stock.get('code', '')
            # 提取6位代码（去掉可能的后缀）
            code_6digit = code[:6] if len(code) >= 6 else code
            if code_6digit and code_6digit not in codes:
                codes.append(code_6digit)
        
        # 批量获取实时价格
        realtime_prices = {}
        if codes:
            try:
                realtime_data = data_engine.realTimePrice(codes)
                for code_6digit, price_info in realtime_data.items():
                    if price_info and 'now' in price_info:
                        realtime_prices[code_6digit] = parse_float(price_info.get('now', 0))
            except Exception as e:
                print(f"  ⚠ 获取实时价格失败: {str(e)}")
        
        # 处理每个持仓
        for stock in stocks:
            code = stock.get('code', '')
            name = stock.get('name', '')
            quantity = parse_int(stock.get('quantity', 0))
            
            # 提取6位代码用于查询实时价格
            code_6digit = code[:6] if len(code) >= 6 else code
            
            if code and quantity > 0:
                # 从实时价格接口获取当前价
                current_price = realtime_prices.get(code_6digit, 0)
                
                positions.append({
                    'code': code,
                    'name': name,
                    'quantity': quantity,
                    'current_price': current_price
                })
                if current_price > 0:
                    print(f"  - {name} ({code}): {quantity} 股, 实时价: {current_price:.3f} 元")
                else:
                    print(f"  - {name} ({code}): {quantity} 股 (无法获取实时价格)")
    else:
        print("\n✓ 当前无持仓")
    
    return available_cash, positions


def sell_all_positions(executor: TongHuaShunExecutor, positions: List[Dict[str, Any]], 
                      data_engine: DataEngine) -> bool:
    """
    市价卖出所有持仓（使用 price_mode="market"，比当前价低1%，实时获取价格）
    
    Args:
        executor: TongHuaShunExecutor 实例
        positions: 持仓列表，每个持仓包含 'code', 'name', 'quantity'
        data_engine: DataEngine 实例，用于获取实时价格
        
    Returns:
        是否全部卖出成功
    """
    if not positions:
        print("\n" + "="*60)
        print("步骤2: 卖出所有持仓")
        print("="*60)
        print("✓ 无持仓需要卖出")
        return True
    
    print("\n" + "="*60)
    print("步骤2: 市价卖出所有持仓（使用市价单，比实时价低1%）")
    print("="*60)
    
    success_count = 0
    for i, pos in enumerate(positions, 1):
        code = pos['code']
        name = pos['name']
        quantity = pos['quantity']
        
        # 提取6位代码用于查询实时价格
        code_6digit = code[:6] if len(code) >= 6 else code
        
        # 实时获取当前价格
        try:
            realtime_data = data_engine.realTimePrice(code_6digit)
            if code_6digit in realtime_data and realtime_data[code_6digit]:
                current_price = parse_float(realtime_data[code_6digit].get('now', 0))
            else:
                current_price = 0
        except Exception as e:
            print(f"  ⚠ 获取 {name} ({code}) 实时价格失败: {str(e)}")
            current_price = 0
        
        if current_price > 0:
            print(f"\n[{i}/{len(positions)}] 卖出: {name} ({code})")
            print(f"  实时价: {current_price:.3f} 元, 数量: {quantity} 股")
            print(f"  使用市价单（比实时价低1%）")
            
            # 市价卖出：使用 price_mode="market"，传入当前价作为基准价格
            # 函数内部会自动计算比基准价低1%的价格
            if executor.press_f2_sell(
                stock_code_or_name=code,
                price=str(current_price),  # 基准价格
                quantity=str(quantity),
                price_mode="market"  # 市价单模式
            ):
                print(f"  ✓ 卖出指令已提交")
                success_count += 1
            else:
                print(f"  ✗ 卖出失败")
        else:
            print(f"\n[{i}/{len(positions)}] 卖出: {name} ({code}), 数量: {quantity} 股")
            print(f"  警告: 无法获取实时价格，跳过该股票")
        
        # 每次卖出后等待，避免操作过快
        time.sleep(1.0)
    
    print(f"\n卖出完成: {success_count}/{len(positions)} 只股票卖出成功")
    
    # 等待卖出操作完成（可能需要一些时间）
    if success_count > 0:
        print("\n等待卖出操作完成...")
        time.sleep(3.0)
    
    return success_count == len(positions)


def buy_etfs_by_price(executor: TongHuaShunExecutor, etf_list: List[Dict[str, Any]], 
                      available_cash: float, data_engine: DataEngine) -> bool:
    """
    按照价格从低到高买入 ETF 列表，每个ETF买一手（100股），直到资金用尽（使用 price_mode="market"，比实时价高1%）
    
    Args:
        executor: TongHuaShunExecutor 实例
        etf_list: ETF 列表，每个元素包含 'name', 'code'
        available_cash: 可用资金
        data_engine: DataEngine 实例，用于获取实时价格
        
    Returns:
        是否成功执行买入操作
    """
    print("\n" + "="*60)
    print("步骤3: 按价格从低到高买入 ETF（每个ETF买一手，使用市价单，比实时价高1%）")
    print("="*60)
    
    # 批量获取所有ETF的实时价格
    codes = [etf['code'] for etf in etf_list]
    realtime_prices = {}
    
    print("\n正在获取ETF实时价格...")
    try:
        realtime_data = data_engine.realTimePrice(codes)
        for code, price_info in realtime_data.items():
            if price_info and 'now' in price_info:
                realtime_prices[code] = parse_float(price_info.get('now', 0))
    except Exception as e:
        print(f"  ⚠ 批量获取实时价格失败: {str(e)}")
        print("  将逐个获取价格...")
    
    # 为每个ETF添加实时价格，并过滤掉无法获取价格的ETF
    etfs_with_price = []
    for etf in etf_list:
        code = etf['code']
        if code in realtime_prices and realtime_prices[code] > 0:
            etf['price'] = realtime_prices[code]
            etfs_with_price.append(etf)
        else:
            # 如果批量获取失败，尝试单独获取
            try:
                single_data = data_engine.realTimePrice(code)
                if code in single_data and single_data[code]:
                    price = parse_float(single_data[code].get('now', 0))
                    if price > 0:
                        etf['price'] = price
                        etfs_with_price.append(etf)
            except Exception as e:
                print(f"  ⚠ 无法获取 {etf['name']} ({code}) 的实时价格: {str(e)}")
    
    if not etfs_with_price:
        print("❌ 无法获取任何ETF的实时价格，无法执行买入操作")
        return False
    
    # 按价格从低到高排序
    sorted_etfs = sorted(etfs_with_price, key=lambda x: x['price'])
    
    print(f"\nETF 列表（按实时价格从低到高）:")
    for i, etf in enumerate(sorted_etfs, 1):
        print(f"  {i}. {etf['name']} ({etf['code']}): 实时价 {etf['price']:.3f} 元")
    
    print(f"\n可用资金: {available_cash:.2f} 元")
    print("\n开始买入...")
    
    remaining_cash = available_cash
    success_count = 0
    
    for i, etf in enumerate(sorted_etfs, 1):
        code = etf['code']
        name = etf['name']
        current_price = etf['price']  # 实时价格
        
        # 每个ETF只买一手（100股）
        shares_per_etf = 100
        
        # 计算市价买入价格：实时价 * 1.01（比实时价高1%，用于计算所需资金）
        # 注意：实际买入价格会在 press_f1_buy 中自动计算
        estimated_buy_price = current_price * 1.01
        required_cash = estimated_buy_price * shares_per_etf
        
        # 检查资金是否足够买入一手
        if remaining_cash < required_cash:
            print(f"\n[{i}/{len(sorted_etfs)}] {name} ({code}): 资金不足（需要 {required_cash:.2f} 元，剩余 {remaining_cash:.2f} 元），停止买入")
            break
        
        print(f"\n[{i}/{len(sorted_etfs)}] 买入: {name} ({code})")
        print(f"  实时价: {current_price:.3f} 元, 数量: {shares_per_etf} 股（一手）")
        print(f"  使用市价单（比实时价高1%），预计金额: {required_cash:.2f} 元")
        
        # 市价买入：使用 price_mode="market"，传入实时价作为基准价格
        # 函数内部会自动计算比基准价高1%的价格
        if executor.press_f1_buy(
            stock_code_or_name=code,
            price=str(current_price),  # 基准价格（实时价）
            quantity=str(shares_per_etf),  # 固定100股
            price_mode="market"  # 市价单模式
        ):
            print(f"  ✓ 买入指令已提交")
            success_count += 1
            remaining_cash -= required_cash
            print(f"  剩余资金: {remaining_cash:.2f} 元")
        else:
            print(f"  ✗ 买入失败")
        
        # 每次买入后等待，避免操作过快
        time.sleep(1.0)
    
    print(f"\n买入完成: {success_count}/{len(sorted_etfs)} 只 ETF 买入成功")
    print(f"剩余资金: {remaining_cash:.2f} 元")
    
    return success_count > 0


def main():
    """
    主函数：执行完整的 ETF 重新平衡流程
    """
    print("\n" + "="*60)
    print("ETF 重新平衡程序")
    print("="*60)
    
    # 创建数据引擎实例（用于获取实时价格）
    try:
        data_engine = DataEngine()
        print("✓ 数据引擎初始化成功")
    except Exception as e:
        print(f"❌ 数据引擎初始化失败: {e}")
        return
    
    # 配置同花顺程序路径（请根据实际情况修改）
    exe_path = r"D:\Program Files (x86)\ths\同花顺\xiadan.exe"
    
    # 创建执行器
    executor = TongHuaShunExecutor(exe_path)
    
    # 方式1: 启动新程序
    if not executor.launch_program():
        # 方式2: 激活已运行的程序
        if not executor.activate_window():
            print("❌ 无法启动或激活程序，请检查程序路径或确保程序已运行")
            return
        else:
            print("✓ 窗口激活成功")
            time.sleep(2)
    else:
        print("✓ 程序启动成功")
        time.sleep(3)  # 等待程序完全加载
    
    try:
        # # 步骤1: 获取当前可用余额和持仓
        # available_cash, positions = get_current_position(executor, data_engine)
        
        # if available_cash <= 0 and not positions:
        #     print("\n❌ 无可用资金且无持仓，无法执行操作")
        #     return
        
        # # 步骤2: 市价卖出所有持仓（使用实时价格）
        # sell_all_positions(executor, positions, data_engine)
        
        # # 等待卖出完成，然后重新查询可用余额
        # print("\n等待卖出完成并重新查询可用余额...")
        # time.sleep(5.0)
        
        # 重新查询可用余额（卖出后资金会增加）
        available_cash, _ = get_current_position(executor, data_engine)
        
        if available_cash <= 0:
            print("\n❌ 可用资金不足，无法买入 ETF")
            return
        
        # 步骤3: 按照价格从低到高买入 ETF（使用实时价格）
        buy_etfs_by_price(executor, target_etfs, available_cash, data_engine)
        
        print("\n" + "="*60)
        print("✓ ETF 重新平衡完成")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断操作")
    except Exception as e:
        print(f"\n\n❌ 执行过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

