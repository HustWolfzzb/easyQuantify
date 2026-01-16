"""
T0 马丁战法策略
马丁网格交易策略，适用于T+0交易的ETF
"""

import json
import os
import time
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime

# 添加项目根目录到 Python 路径
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from Trade.TongHuaShunExecutor import TongHuaShunExecutor
from DataEngine.Data import realTimePrice


class T0Martingale:
    """T0马丁战法策略类"""
    
    def __init__(self, config_path: str = "Strategy/T0Martingale.json", 
                 executor: Optional[TongHuaShunExecutor] = None):
        """
        初始化策略
        
        Args:
            config_path: 配置文件路径
            executor: 交易执行器，如果为None则需要在start时提供
        """
        self.config_path = config_path
        self.executor = executor
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return {"etfs": {}}
        return {"etfs": {}}
    
    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def _get_price(self, code: str) -> Optional[float]:
        """获取ETF当前价格"""
        try:
            data = realTimePrice(code)
            if code in data and 'now' in data[code]:
                return float(data[code]['now'])
        except Exception as e:
            print(f"获取 {code} 价格失败: {e}")
        return None
    
    def _calculate_order_amount(self, etf_config: Dict, add_count: int) -> int:
        """计算订单数量"""
        grid_config = etf_config.get('grid_config', {})
        base_amount = grid_config.get('base_amount', 100)
        amount_mode = grid_config.get('amount_mode', 'multiply')
        
        if amount_mode == 'multiply':
            multiply_factor = grid_config.get('multiply_factor', 2.0)
            return int(base_amount * (multiply_factor ** add_count))
        else:  # accumulate
            accumulate_step = grid_config.get('accumulate_step', 100)
            return base_amount + add_count * accumulate_step
    
    def _place_grid_orders(self, code: str, base_price: float, etf_config: Dict):
        """布置网格订单（仅记录订单，不实际下单，等价格穿越时再下单）"""
        grid_config = etf_config.get('grid_config', {})
        interval = grid_config.get('interval', 0.01)
        max_depth = grid_config.get('max_depth', -1)  # -1表示无限
        
        orders = []
        add_count = 0
        
        while True:
            if max_depth > 0 and add_count >= max_depth:
                break
            
            order_price = round(base_price - interval * (add_count + 1), 3)
            if order_price <= 0:
                break
            
            order_amount = self._calculate_order_amount(etf_config, add_count)
            orders.append({
                "price": order_price,
                "amount": order_amount,
                "filled": False
            })
            
            add_count += 1
        
        etf_config['orders'] = orders
        print(f"  {code} 已规划 {len(orders)} 个网格订单（价格穿越时自动执行）")
    
    def _check_and_add_position(self, code: str, etf_config: Dict, current_price: float):
        """检查价格是否穿越订单价格，如果穿越则加仓"""
        orders = etf_config.get('orders', [])
        positions = etf_config.get('positions', [])
        
        for order in orders:
            if order['filled']:
                continue
            
            order_price = order['price']
            if current_price <= order_price:
                # 价格穿越，执行买入
                order_amount = order['amount']
                
                if self.executor:
                    try:
                        success = self.executor.press_f1_buy(
                            stock_code_or_name=code,
                            price=str(order_price),
                            quantity=str(order_amount),
                            price_mode="market"
                        )
                        if success:
                            order['filled'] = True
                            positions.append({
                                "price": order_price,
                                "amount": order_amount,
                                "cost": order_price * order_amount
                            })
                            
                            # 更新统计信息
                            etf_config['add_count'] = etf_config.get('add_count', 0) + 1
                            total_cost = sum(p['cost'] for p in positions)
                            total_amount = sum(p['amount'] for p in positions)
                            etf_config['total_cost'] = total_cost
                            etf_config['total_amount'] = total_amount
                            etf_config['avg_cost'] = round(total_cost / total_amount, 3) if total_amount > 0 else 0
                            
                            print(f"  {code} 加仓: 价格 {order_price}, 数量 {order_amount}")
                            time.sleep(0.5)
                    except Exception as e:
                        print(f"  {code} 加仓失败: {e}")
    
    def _check_and_sell(self, code: str, etf_config: Dict, current_price: float):
        """检查价格是否超过成本线，如果超过则卖出"""
        avg_cost = etf_config.get('avg_cost', 0)
        if avg_cost <= 0:
            return
        
        if current_price <= avg_cost:
            return
        
        positions = etf_config.get('positions', [])
        manual_amount = etf_config.get('manual_amount', 0)
        
        # 计算可卖数量（策略买入 + 手动买入）
        total_amount = sum(p['amount'] for p in positions) + manual_amount
        
        if total_amount <= 0:
            return
        
        sell_config = etf_config.get('sell_config', {})
        sell_mode = sell_config.get('amount_mode', 'all')
        
        if sell_mode == 'all':
            # 全部卖出
            if self.executor:
                try:
                    success = self.executor.press_f2_sell(
                        stock_code_or_name=code,
                        price=str(current_price),
                        quantity=str(total_amount),
                        price_mode="market"
                    )
                    if success:
                        print(f"  {code} 全部卖出: 价格 {current_price}, 数量 {total_amount}, 成本 {avg_cost:.3f}")
                        # 清空持仓和订单
                        etf_config['positions'] = []
                        etf_config['orders'] = []
                        etf_config['total_cost'] = 0
                        etf_config['total_amount'] = 0
                        etf_config['avg_cost'] = 0
                        etf_config['add_count'] = 0
                        etf_config['manual_amount'] = 0
                        etf_config['status'] = 'stopped'
                        time.sleep(0.5)
                except Exception as e:
                    print(f"  {code} 卖出失败: {e}")
        else:
            # 按网格卖出
            sell_interval = sell_config.get('interval', 0.01)
            sell_base_amount = sell_config.get('base_amount', 100)
            sell_count = 0
            remaining_amount = total_amount
            
            while remaining_amount > 0 and current_price > avg_cost:
                sell_price = round(avg_cost + sell_interval * (sell_count + 1), 3)
                if current_price < sell_price:
                    break
                
                sell_amount = min(sell_base_amount, remaining_amount)
                if self.executor:
                    try:
                        success = self.executor.press_f2_sell(
                            stock_code_or_name=code,
                            price=str(sell_price),
                            quantity=str(sell_amount),
                            price_mode="market"
                        )
                        if success:
                            print(f"  {code} 卖出: 价格 {sell_price}, 数量 {sell_amount}")
                            remaining_amount -= sell_amount
                            sell_count += 1
                            
                            # 更新持仓（优先卖出策略买入的）
                            sold = sell_amount
                            for pos in positions[:]:
                                if sold <= 0:
                                    break
                                if pos['amount'] <= sold:
                                    sold -= pos['amount']
                                    positions.remove(pos)
                                else:
                                    pos['amount'] -= sold
                                    pos['cost'] = pos['price'] * pos['amount']
                                    sold = 0
                            
                            # 更新手动买入数量
                            if sold > 0 and manual_amount > 0:
                                manual_amount = max(0, manual_amount - sold)
                                etf_config['manual_amount'] = manual_amount
                            
                            # 更新统计
                            total_cost = sum(p['cost'] for p in positions)
                            total_amount = sum(p['amount'] for p in positions) + manual_amount
                            etf_config['total_cost'] = total_cost
                            etf_config['total_amount'] = total_amount
                            etf_config['avg_cost'] = round(total_cost / total_amount, 3) if total_amount > 0 else 0
                            
                            time.sleep(0.5)
                    except Exception as e:
                        print(f"  {code} 卖出失败: {e}")
                        break
    
    def start_etf(self, code: str, executor: Optional[TongHuaShunExecutor] = None):
        """启动指定ETF的策略"""
        if executor:
            self.executor = executor
        
        if not self.executor:
            print("错误: 未提供交易执行器")
            return
        
        if 'etfs' not in self.config:
            self.config['etfs'] = {}
        
        if code not in self.config['etfs']:
            self.config['etfs'][code] = {
                "status": "not_started",
                "base_price": 0,
                "current_price": 0,
                "grid_config": {
                    "max_depth": -1,
                    "interval": 0.01,
                    "amount_mode": "multiply",
                    "base_amount": 100,
                    "multiply_factor": 2.0
                },
                "orders": [],
                "positions": [],
                "add_count": 0,
                "total_cost": 0,
                "total_amount": 0,
                "avg_cost": 0,
                "manual_amount": 0,
                "sell_config": {
                    "interval": 0.01,
                    "amount_mode": "all"
                }
            }
        
        etf_config = self.config['etfs'][code]
        
        if etf_config['status'] == 'not_started':
            # 获取最新价格
            current_price = self._get_price(code)
            if not current_price:
                print(f"无法获取 {code} 的价格，启动失败")
                return
            
            etf_config['base_price'] = current_price
            etf_config['current_price'] = current_price
            etf_config['status'] = 'running'
            
            print(f"启动 {code} 策略，基准价格: {current_price}")
            
            # 布置网格订单
            self._place_grid_orders(code, current_price, etf_config)
        
        self._save_config()
    
    def add_manual_position(self, code: str, amount: int):
        """添加手动买入的持仓"""
        if code not in self.config.get('etfs', {}):
            print(f"错误: {code} 未在配置中")
            return
        
        etf_config = self.config['etfs'][code]
        etf_config['manual_amount'] = etf_config.get('manual_amount', 0) + amount
        self._save_config()
        print(f"{code} 手动买入 {amount} 股，总手动持仓: {etf_config['manual_amount']}")
    
    def monitor(self, codes: Optional[List[str]] = None, executor: Optional[TongHuaShunExecutor] = None):
        """监控价格并执行策略"""
        if executor:
            self.executor = executor
        
        if not self.executor:
            print("错误: 未提供交易执行器")
            return
        
        if codes is None:
            codes = list(self.config.get('etfs', {}).keys())
        
        print(f"\n开始监控 {len(codes)} 个ETF...")
        print("=" * 60)
        
        while True:
            try:
                for code in codes:
                    if code not in self.config.get('etfs', {}):
                        continue
                    
                    etf_config = self.config['etfs'][code]
                    if etf_config.get('status') != 'running':
                        continue
                    
                    # 获取当前价格
                    current_price = self._get_price(code)
                    if not current_price:
                        continue
                    
                    etf_config['current_price'] = current_price
                    
                    # 检查是否需要加仓
                    self._check_and_add_position(code, etf_config, current_price)
                    
                    # 检查是否需要卖出
                    self._check_and_sell(code, etf_config, current_price)
                    
                    # 保存配置
                    self._save_config()
                
                time.sleep(3)  # 每3秒检测一次
                
            except KeyboardInterrupt:
                print("\n监控已停止")
                break
            except Exception as e:
                print(f"监控出错: {e}")
                time.sleep(3)


def main():
    """主函数"""
    # 配置同花顺程序路径
    exe_path = r"D:\Program Files (x86)\ths\同花顺\xiadan.exe"
    
    # 创建执行器
    executor = TongHuaShunExecutor(exe_path)
    
    # 激活窗口
    if not executor.activate_window():
        if not executor.launch_program():
            print("无法启动或激活程序")
            return
    
    time.sleep(2)
    
    # 创建策略
    strategy = T0Martingale(executor=executor)
    
    # 示例：启动ETF策略
    # strategy.start_etf('159695')  # 通信ETF
    
    # 开始监控
    # strategy.monitor(['159695'])


if __name__ == '__main__':
    main()

