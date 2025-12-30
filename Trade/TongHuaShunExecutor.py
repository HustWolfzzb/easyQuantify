"""
同花顺下单程序执行器
使用 Windows 窗口操作和图像识别来实现自动化交易
"""

import os
import sys
import time
import subprocess
import io
import json
import logging
import glob
from typing import Dict, Tuple, Optional, List, Any
from datetime import datetime, time as dt_time, timezone, timedelta
import win32gui
import win32con
import win32process
import win32api
import win32clipboard
from PIL import ImageGrab, Image
import cv2
import numpy as np

# 添加项目根目录到 Python 路径，以便导入 VLMImageAnalyzer
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# 延迟导入 VLMImageAnalyzer（避免初始化时失败）
VLM_AVAILABLE = False
try:
    from LLM.VLMImageAnalyzer import VLMImageAnalyzer
    VLM_AVAILABLE = True
except ImportError:
    VLM_AVAILABLE = False
    # 此时logger还未初始化，使用print
    print("警告: VLMImageAnalyzer 未安装，F4 查询功能将无法使用 VLM 分析")


class SystemLogger:
    """
    系统日志管理器
    管理截图、资产JSON等文件，并提供定期清理功能
    """
    
    def __init__(self, base_dir: str = "SystemLog", retention_days: int = 7):
        """
        初始化日志管理器
        
        Args:
            base_dir: 日志根目录，默认为 "SystemLog"
            retention_days: 文件保留天数，默认7天
        """
        # @FIX 新增了日志系统，还胡自动清理。
        self.base_dir = base_dir
        self.retention_days = retention_days
        
        # 创建子目录
        self.screenshots_dir = os.path.join(base_dir, "screenshots")
        self.assets_dir = os.path.join(base_dir, "assets")
        self.logs_dir = os.path.join(base_dir, "logs")
        
        # 创建目录
        for dir_path in [self.screenshots_dir, self.assets_dir, self.logs_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
        
        # 初始化日志记录器
        self.logger = self._init_logger()
        
        # 执行清理（如果距离上次清理超过一天，则清理）
        self._cleanup_if_needed()
    
    def _init_logger(self) -> logging.Logger:
        """初始化Python logging"""
        logger = logging.getLogger("TongHuaShunExecutor")
        logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if logger.handlers:
            return logger
        
        # 文件handler
        log_file = os.path.join(self.logs_dir, f"executor_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # 控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        return logger
    
    def _get_last_cleanup_time(self) -> Optional[datetime]:
        """获取上次清理时间"""
        cleanup_file = os.path.join(self.base_dir, ".last_cleanup")
        if os.path.exists(cleanup_file):
            try:
                with open(cleanup_file, 'r') as f:
                    timestamp_str = f.read().strip()
                    return datetime.fromisoformat(timestamp_str)
            except:
                return None
        return None
    
    def _save_cleanup_time(self):
        """保存清理时间"""
        cleanup_file = os.path.join(self.base_dir, ".last_cleanup")
        try:
            with open(cleanup_file, 'w') as f:
                f.write(datetime.now().isoformat())
        except:
            pass
    
    def _cleanup_if_needed(self):
        """如果需要，执行清理操作（每天最多清理一次）"""
        last_cleanup = self._get_last_cleanup_time()
        now = datetime.now()
        
        # 如果从未清理过，或者距离上次清理超过1天，则清理
        if last_cleanup is None or (now - last_cleanup).days >= 1:
            self.cleanup_old_files()
            self._save_cleanup_time()
    
    def cleanup_old_files(self):
        """清理过期文件"""
        cutoff_time = datetime.now() - timedelta(days=self.retention_days)
        deleted_count = 0
        
        # 清理截图文件
        for pattern in [os.path.join(self.screenshots_dir, "*.png"),
                       os.path.join(self.screenshots_dir, "*.jpg"),
                       os.path.join(self.assets_dir, "*.json")]:
            for file_path in glob.glob(pattern):
                try:
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                except Exception as e:
                    self.logger.warning(f"清理文件失败 {file_path}: {e}")
        
        if deleted_count > 0:
            self.logger.info(f"清理完成，删除了 {deleted_count} 个过期文件（超过{self.retention_days}天）")
        else:
            self.logger.debug("无需清理，没有过期文件")
    
    def get_screenshot_path(self, filename: Optional[str] = None) -> str:
        """获取截图保存路径"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        return os.path.join(self.screenshots_dir, filename)
    
    def get_asset_path(self, filename: Optional[str] = None) -> str:
        """获取资产JSON保存路径"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"asset_data_{timestamp}.json"
        return os.path.join(self.assets_dir, filename)
    
    def save_asset_data(self, asset_data: Dict[str, Any], filename: Optional[str] = None) -> str:
        """保存资产数据到JSON文件"""
        file_path = self.get_asset_path(filename)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(asset_data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"资产数据已保存: {file_path}")
            return file_path
        except Exception as e:
            self.logger.error(f"保存资产数据失败: {e}")
            raise
    
    def info(self, message: str):
        """记录信息日志"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """记录警告日志"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """记录错误日志"""
        self.logger.error(message)
    
    def debug(self, message: str):
        """记录调试日志"""
        self.logger.debug(message)


class TongHuaShunExecutor:
    """
    同花顺执行器类
    通过 Windows 窗口操作和图像识别来控制 xiadan.exe 程序
    """
    
    def __init__(self, exe_path: str, screenshot_dir: str = None, log_dir: str = "SystemLog"):
        """
        初始化执行器
        
        Args:
            exe_path: xiadan.exe 程序的完整路径
            screenshot_dir: 截图保存目录（已废弃，保留用于兼容性，实际使用SystemLog/screenshots）
            log_dir: 日志根目录，默认为 "SystemLog"
        """
        self.exe_path = exe_path
        self.hwnd = None  # 窗口句柄
        self.window_rect = None  # 窗口坐标 (left, top, right, bottom)
        
        # 初始化日志管理器
        self.logger = SystemLogger(base_dir=log_dir, retention_days=7)
        self.screenshot_dir = self.logger.screenshots_dir  # 使用logger管理的目录
        
        # 如果旧截图目录存在且与新目录不同，提示用户
        if screenshot_dir and screenshot_dir != self.screenshot_dir and os.path.exists(screenshot_dir):
            self.logger.warning(f"检测到旧截图目录 '{screenshot_dir}'，新截图将保存到 '{self.screenshot_dir}'")
        
        # 股票名称到代码的转换字典（可维护）
        self.stock_name_to_code = {
            # 示例：'平安银行': '000001', '万科A': '000002'
            # 用户可以在这里维护股票名称和代码的映射关系
        }
        
        # 初始化 VLM 分析器（如果可用）
        self.vlm_analyzer = None
        if VLM_AVAILABLE:
            try:
                self.vlm_analyzer = VLMImageAnalyzer()
                self.logger.info("VLM 分析器初始化成功")
            except Exception as e:
                self.logger.warning(f"VLM 分析器初始化失败: {e}")
                self.vlm_analyzer = None
        
        # 界面元素识别结果缓存
        self.ui_elements = {}  # {元素名称: (中心坐标, 类型)}
    
    def find_window_by_process(self, process_name: str = "xiadan.exe") -> Optional[int]:
        """
        通过进程名查找窗口句柄
        
        Args:
            process_name: 进程名称
            
        Returns:
            窗口句柄，如果未找到返回 None
        """
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    process = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid)
                    exe_name = win32process.GetModuleFileNameEx(process, 0)
                    if process_name.lower() in exe_name.lower():
                        # 获取窗口信息用于验证
                        window_title = win32gui.GetWindowText(hwnd)
                        window_class = win32gui.GetClassName(hwnd)
                        # 过滤掉任务栏、桌面等系统窗口
                        if window_class.lower() not in ['shell_traywnd', 'progman', 'workerw', 'button']:
                            windows.append((hwnd, window_title, window_class, exe_name))
                except:
                    pass
            return True
        
        windows = []
        win32gui.EnumWindows(callback, windows)
        
        if windows:
            # 打印所有找到的窗口信息（调试信息）
            # 注意：此时logger可能还未初始化，使用print
            print(f"找到 {len(windows)} 个可能的窗口:")
            for i, (hwnd, title, cls, exe) in enumerate(windows):
                rect = win32gui.GetWindowRect(hwnd)
                print(f"  [{i}] 句柄: {hwnd}, 标题: '{title}', 类名: '{cls}', 坐标: {rect}")
            
            # 优先选择有标题的窗口，且标题包含"下单"相关关键词
            for hwnd, title, cls, exe in windows:
                if title and ('下单' in title or '交易' in title or '委托' in title):
                    print(f"选择窗口: 句柄={hwnd}, 标题='{title}'")
                    return hwnd
            
            # 如果没有匹配标题的，选择第一个非系统窗口
            print(f"选择第一个窗口: 句柄={windows[0][0]}, 标题='{windows[0][1]}'")
            return windows[0][0]
        return None
    
    def find_window_by_title(self, title_keyword: str = "下单") -> Optional[int]:
        """
        通过窗口标题查找窗口句柄
        
        Args:
            title_keyword: 窗口标题关键词
            
        Returns:
            窗口句柄，如果未找到返回 None
        """
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title_keyword in window_title:
                    windows.append(hwnd)
            return True
        
        windows = []
        win32gui.EnumWindows(callback, windows)
        
        if windows:
            return windows[0]
        return None
    
    def get_window_rect(self, hwnd: int, use_client_area: bool = False) -> Tuple[int, int, int, int]:
        """
        获取窗口坐标
        
        Args:
            hwnd: 窗口句柄
            use_client_area: 是否使用客户区（不包括标题栏和边框），默认 False 使用整个窗口
            
        Returns:
            (left, top, right, bottom) 窗口坐标（屏幕坐标）
        """
        try:
            # 检查窗口是否有效
            if not win32gui.IsWindow(hwnd):
                raise ValueError("窗口句柄无效")
            
            if use_client_area:
                # 获取客户区矩形（不包括标题栏和边框）
                client_rect = win32gui.GetClientRect(hwnd)
                client_left, client_top, client_right, client_bottom = client_rect
                
                # 将客户区左上角坐标转换为屏幕坐标
                screen_left, screen_top = win32gui.ClientToScreen(hwnd, (client_left, client_top))
                
                # 将客户区右下角坐标转换为屏幕坐标
                screen_right, screen_bottom = win32gui.ClientToScreen(hwnd, (client_right, client_bottom))
                
                return (screen_left, screen_top, screen_right, screen_bottom)
            else:
                # 使用整个窗口矩形（包含标题栏和边框）
                rect = win32gui.GetWindowRect(hwnd)
                return rect
        except Exception as e:
            # 注意：此时可能logger还未初始化，需要检查
            if hasattr(self, 'logger'):
                self.logger.error(f"获取窗口坐标失败: {e}")
            else:
                print(f"获取窗口坐标失败: {e}")
            # 如果失败，尝试使用 GetWindowRect（包含标题栏）
            try:
                rect = win32gui.GetWindowRect(hwnd)
                return rect
            except:
                return (0, 0, 0, 0)
    
    def focus_window(self, hwnd: int) -> bool:
        """
        聚焦到指定窗口，确保窗口在前台且不被最小化
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            是否成功聚焦
        """
        try:
            # 检查窗口是否有效
            if not win32gui.IsWindow(hwnd):
                if hasattr(self, 'logger'):
                    self.logger.error("窗口句柄无效")
                else:
                    print("窗口句柄无效")
                return False
            
            # 检查窗口是否最小化
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMINIMIZED:
                # 恢复窗口
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.2)
            
            # 确保窗口可见（不是最小化）
            if not win32gui.IsWindowVisible(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                time.sleep(0.1)
            
            # 将窗口置于前台
            # 使用多种方法确保窗口在前台
            try:
                # 方法1: SetForegroundWindow（需要满足特定条件）
                win32gui.SetForegroundWindow(hwnd)
            except:
                # 如果失败，尝试其他方法
                try:
                    # 方法2: 先最小化再恢复（可以绕过某些限制）
                    win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                    time.sleep(0.1)
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    time.sleep(0.1)
                    win32gui.SetForegroundWindow(hwnd)
                except:
                    pass
            
            # 激活窗口
            try:
                win32gui.SetFocus(hwnd)
            except:
                pass
            
            # 确保窗口在最上层（可选，某些窗口可能不支持）
            try:
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, 0, 0, 
                                     win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            except:
                pass
            
            time.sleep(0.15)  # 等待窗口完全响应
            
            # 再次检查窗口状态，确保没有被最小化
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMINIMIZED:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.1)
            
            return True
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"聚焦窗口时出错: {e}")
            else:
                print(f"聚焦窗口时出错: {e}")
            return False
    
    def launch_program(self) -> bool:
        """
        启动 xiadan.exe 程序
        
        Returns:
            是否成功启动
        """
        if not os.path.exists(self.exe_path):
            self.logger.error(f"程序路径不存在: {self.exe_path}")
            return False
        
        try:
            # 启动程序
            subprocess.Popen(self.exe_path)
            time.sleep(2)  # 等待程序启动
            
            # 查找窗口
            self.hwnd = self.find_window_by_process("xiadan.exe")
            if not self.hwnd:
                self.hwnd = self.find_window_by_title("下单")
            
            if self.hwnd:
                # 获取窗口信息用于验证
                window_title = win32gui.GetWindowText(self.hwnd)
                window_class = win32gui.GetClassName(self.hwnd)
                
                # 获取窗口坐标
                self.window_rect = self.get_window_rect(self.hwnd)
                # 聚焦窗口
                self.focus_window(self.hwnd)
                
                left, top, right, bottom = self.window_rect
                width = right - left
                height = bottom - top
                self.logger.info(f"程序启动成功")
                self.logger.info(f"  窗口句柄: {self.hwnd}")
                self.logger.info(f"  窗口标题: '{window_title}'")
                self.logger.info(f"  窗口类名: '{window_class}'")
                self.logger.info(f"  客户区坐标: {self.window_rect}")
                self.logger.info(f"  客户区尺寸: {width}x{height}")
                return True
            else:
                self.logger.error("无法找到程序窗口")
                return False
        except Exception as e:
            self.logger.error(f"启动程序失败: {e}")
            return False
    
    def activate_window(self) -> bool:
        """
        激活已运行的程序窗口
        
        Returns:
            是否成功激活
        """
        # 先尝试通过进程名查找
        self.hwnd = self.find_window_by_process("xiadan.exe")
        if not self.hwnd:
            # 再尝试通过窗口标题查找
            self.hwnd = self.find_window_by_title("下单")
        
        if self.hwnd:
            # 获取窗口信息用于验证
            window_title = win32gui.GetWindowText(self.hwnd)
            window_class = win32gui.GetClassName(self.hwnd)
            
            # 获取窗口坐标
            self.window_rect = self.get_window_rect(self.hwnd)
            # 聚焦窗口
            if self.focus_window(self.hwnd):
                left, top, right, bottom = self.window_rect
                width = right - left
                height = bottom - top
                self.logger.info(f"窗口激活成功")
                self.logger.info(f"  窗口句柄: {self.hwnd}")
                self.logger.info(f"  窗口标题: '{window_title}'")
                self.logger.info(f"  窗口类名: '{window_class}'")
                self.logger.info(f"  客户区坐标: {self.window_rect}")
                self.logger.info(f"  客户区尺寸: {width}x{height}")
                return True
        
        self.logger.error("无法找到程序窗口，请先启动程序")
        return False
    
    def capture_window(self, save_path: Optional[str] = None) -> Optional[Image.Image]:
        """
        对程序窗口进行截图
        
        Args:
            save_path: 保存路径，如果为 None 则自动生成
            
        Returns:
            PIL Image 对象，失败返回 None
        """
        if not self.hwnd or not self.window_rect:
            self.logger.error("窗口未激活，请先启动或激活程序")
            return None
        
        try:
            # 聚焦窗口，确保窗口在前台
            if not self.focus_window(self.hwnd):
                self.logger.warning("无法聚焦窗口，尝试继续...")
            
            time.sleep(0.2)  # 等待窗口完全显示
            
            # 重新获取窗口坐标（窗口可能移动了）
            # 使用整个窗口矩形，确保截取完整窗口
            self.window_rect = self.get_window_rect(self.hwnd, use_client_area=False)
            left, top, right, bottom = self.window_rect
            width = right - left
            height = bottom - top
            
            self.logger.debug(f"窗口坐标: ({left}, {top}, {right}, {bottom})")
            self.logger.debug(f"窗口尺寸: {width}x{height}")
            
            # 验证窗口尺寸和坐标是否合理
            if width <= 0 or height <= 0:
                self.logger.error(f"窗口尺寸无效 ({width}x{height})")
                self.logger.error(f"坐标: left={left}, top={top}, right={right}, bottom={bottom}")
                return None
            
            if width < 50 or height < 50:
                self.logger.warning(f"窗口尺寸异常 ({width}x{height})，可能是错误的窗口")
                window_title = win32gui.GetWindowText(self.hwnd)
                self.logger.warning(f"当前窗口标题: '{window_title}'")
                # 即使尺寸异常，也尝试截图
            
            # 确保坐标有效（right > left, bottom > top）
            if right <= left or bottom <= top:
                self.logger.error(f"坐标无效 - left={left}, top={top}, right={right}, bottom={bottom}")
                return None
            
            # 再次确保窗口在前台（截图前）
            try:
                win32gui.SetForegroundWindow(self.hwnd)
                time.sleep(0.1)
            except:
                pass
            
            # 截图
            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            
            # 截图后再次确保窗口在前台（防止被最小化）
            try:
                win32gui.SetForegroundWindow(self.hwnd)
            except:
                pass
            
            # 保存截图
            if save_path is None:
                save_path = self.logger.get_screenshot_path()
            
            screenshot.save(save_path)
            self.logger.info(f"截图已保存: {save_path}")
            
            return screenshot
        except Exception as e:
            self.logger.error(f"截图失败: {e}")
            return None

    def click_element(self, element_name: str, element_type: str = 'auto') -> bool:
        """
        点击界面元素
        
        Args:
            element_name: 元素名称
            element_type: 元素类型 ('button', 'input_box', 'auto')
            
        Returns:
            是否成功点击
        """
        coord = self.get_element_coordinate(element_name, element_type)
        if coord is None:
            return False
        
        try:
            # 聚焦窗口
            self.focus_window(self.hwnd)
            time.sleep(0.1)
            
            # 点击坐标
            win32api.SetCursorPos(coord)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            
            self.logger.info(f"已点击元素: {element_name} 坐标: {coord}")
            return True
        except Exception as e:
            self.logger.error(f"点击元素失败: {e}")
            return False
    
    def input_text(self, element_name: str, text: str) -> bool:
        """
        在输入框中输入文本
        
        Args:
            element_name: 输入框名称
            text: 要输入的文本
            
        Returns:
            是否成功输入
        """
        coord = self.get_element_coordinate(element_name, 'input_box')
        if coord is None:
            return False
        
        try:
            # 聚焦窗口
            self.focus_window(self.hwnd)
            time.sleep(0.1)
            
            # 点击输入框
            win32api.SetCursorPos(coord)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.1)
            
            # 清空输入框（全选并删除）
            # 使用剪贴板方式输入文本
            # 将文本复制到剪贴板
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text)
            win32clipboard.CloseClipboard()
            
            # 发送 Ctrl+V 粘贴
            win32api.keybd_event(0x11, 0, 0, 0)  # Ctrl down
            win32api.keybd_event(0x56, 0, 0, 0)  # V down
            win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)  # V up
            win32api.keybd_event(0x11, 0, win32con.KEYEVENTF_KEYUP, 0)  # Ctrl up
            time.sleep(0.1)
            
            self.logger.info(f"已在 {element_name} 输入文本: {text}")
            return True
        except Exception as e:
            self.logger.error(f"输入文本失败: {e}")
            return False
    
    # ==================== 键盘快捷键控制功能 ====================
    
    def _send_key(self, vk_code: int, wait_time: float = 0.1) -> bool:
        """
        发送键盘按键
        
        Args:
            vk_code: 虚拟键码
            wait_time: 按键后等待时间（秒）
            
        Returns:
            是否成功发送
        """
        try:
            # 确保窗口在前台
            self.focus_window(self.hwnd)
            time.sleep(0.05)
            
            # 按下按键
            win32api.keybd_event(vk_code, 0, 0, 0)
            time.sleep(0.05)
            # 释放按键
            win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)
            
            time.sleep(wait_time)
            return True
        except Exception as e:
            self.logger.error(f"发送按键失败: {e}")
            return False
    
    def _send_backspace(self, times: int = 1, wait_time: float = 0.1) -> bool:
        """
        发送 Backspace 键（模拟人工操作速度）
        
        Args:
            times: 发送次数
            wait_time: 每次按键后等待时间（秒），默认0.1秒模拟人工速度
            
        Returns:
            是否成功
        """
        try:
            self.focus_window(self.hwnd)
            time.sleep(0.1)  # 操作前等待
            
            for _ in range(times):
                win32api.keybd_event(0x08, 0, 0, 0)  # VK_BACK
                time.sleep(0.05)
                win32api.keybd_event(0x08, 0, win32con.KEYEVENTF_KEYUP, 0)
                time.sleep(wait_time)  # 每次删除后等待，模拟人工速度
            
            # 删除完成后额外等待
            time.sleep(0.15)
            return True
        except Exception as e:
            self.logger.error(f"发送 Backspace 失败: {e}")
            return False
    
    def _send_enter(self, times: int = 1, wait_time: float = 0.2) -> bool:
        """
        发送 Enter 键（模拟人工操作速度）
        
        Args:
            times: 发送次数
            wait_time: 每次按键后等待时间（秒），默认0.2秒模拟人工速度
            
        Returns:
            是否成功
        """
        try:
            self.focus_window(self.hwnd)
            time.sleep(0.1)  # 操作前等待
            
            for _ in range(times):
                win32api.keybd_event(0x0D, 0, 0, 0)  # VK_RETURN (Enter)
                time.sleep(0.05)
                win32api.keybd_event(0x0D, 0, win32con.KEYEVENTF_KEYUP, 0)
                time.sleep(wait_time)  # 每次 Enter 后等待，确保界面响应
            
            # Enter 完成后额外等待，确保界面切换完成
            time.sleep(0.2)
            return True
        except Exception as e:
            self.logger.error(f"发送 Enter 失败: {e}")
            return False
    
    def _char_to_vk(self, char: str) -> Optional[int]:
        """
        将字符转换为虚拟键码
        
        Args:
            char: 单个字符
            
        Returns:
            虚拟键码，如果无法转换返回 None
        """
        char = char.upper()
        
        # 数字 0-9
        if '0' <= char <= '9':
            return ord(char)
        
        # 字母 A-Z
        if 'A' <= char <= 'Z':
            return ord(char)
        
        # 特殊字符映射
        special_chars = {
            '.': 0xBE,  # VK_OEM_PERIOD (.)
            '-': 0xBD,  # VK_OEM_MINUS (-)
            '+': 0xBB,  # VK_OEM_PLUS (+)
            '/': 0xBF,  # VK_OEM_2 (/)
            ' ': 0x20,  # VK_SPACE
        }
        
        if char in special_chars:
            return special_chars[char]
        
        return None
    
    def _send_text(self, text: str, wait_time: float = 0.15) -> bool:
        """
        逐字符输入文本（使用直接键盘输入，模拟人工操作速度）
        
        Args:
            text: 要输入的文本
            wait_time: 每个字符输入后等待时间（秒），默认0.15秒模拟人工速度
            
        Returns:
            是否成功
        """
        try:
            self.focus_window(self.hwnd)
            time.sleep(0.2)  # 输入前等待，确保窗口已聚焦
            
            for char in text:
                vk_code = self._char_to_vk(char)
                
                if vk_code is None:
                    # 如果无法转换为虚拟键码，尝试使用剪贴板方式
                    self.logger.warning(f"字符 '{char}' 无法直接输入，尝试使用剪贴板方式")
                    try:
                        win32clipboard.OpenClipboard()
                        win32clipboard.EmptyClipboard()
                        win32clipboard.SetClipboardText(char)
                        win32clipboard.CloseClipboard()
                        
                        win32api.keybd_event(0x11, 0, 0, 0)  # Ctrl down
                        time.sleep(0.05)
                        win32api.keybd_event(0x56, 0, 0, 0)  # V down
                        time.sleep(0.05)
                        win32api.keybd_event(0x56, 0, win32con.KEYEVENTF_KEYUP, 0)  # V up
                        time.sleep(0.05)
                        win32api.keybd_event(0x11, 0, win32con.KEYEVENTF_KEYUP, 0)  # Ctrl up
                    except Exception as e:
                        self.logger.error(f"剪贴板输入也失败: {e}")
                        continue
                else:
                    # 使用直接键盘输入（更可靠）
                    # 检查是否需要 Shift（对于特殊字符）
                    need_shift = False
                    if char == '.' or char == '-' or char == '+' or char == '/':
                        # 这些字符在数字键盘区域，不需要 Shift
                        pass
                    elif char.isupper() and not char.isdigit():
                        # 大写字母需要 Shift
                        need_shift = True
                    
                    # 按下 Shift（如果需要）
                    if need_shift:
                        win32api.keybd_event(0x10, 0, 0, 0)  # VK_SHIFT
                        time.sleep(0.02)
                    
                    # 按下并释放字符键
                    win32api.keybd_event(vk_code, 0, 0, 0)
                    time.sleep(0.05)
                    win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)
                    
                    # 释放 Shift（如果按下了）
                    if need_shift:
                        time.sleep(0.02)
                        win32api.keybd_event(0x10, 0, win32con.KEYEVENTF_KEYUP, 0)
                
                # 每个字符输入后等待，模拟人工输入速度
                time.sleep(wait_time)
            
            # 输入完成后额外等待，确保内容已输入
            time.sleep(0.3)
            return True
        except Exception as e:
            self.logger.error(f"输入文本失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _get_stock_code(self, stock_input: str) -> str:
        """
        将股票名称或代码转换为代码
        
        Args:
            stock_input: 股票名称或代码
            
        Returns:
            股票代码
        """
        # 如果输入的是代码（纯数字），直接返回
        if stock_input.isdigit():
            return stock_input
        
        # 如果输入的是名称，从字典中查找
        if stock_input in self.stock_name_to_code:
            return self.stock_name_to_code[stock_input]
        
        # 如果找不到，返回原输入（可能是代码格式不同）
        self.logger.warning(f"未找到股票 '{stock_input}' 的代码映射，使用原输入")
        return stock_input
    
    def _get_price_decimal_places(self, price_str: str) -> int:
        """
        获取价格字符串的小数位数
        
        Args:
            price_str: 价格字符串，如 "10.50" 或 "10.5" 或 "10.500"
            
        Returns:
            小数位数，如果没有小数部分返回 0
        """
        if '.' not in price_str:
            return 0
        decimal_part = price_str.split('.')[1]
        # 返回原始小数位数（包括末尾的0）
        # 例如 "10.50" 返回 2，"10.5" 返回 1，"10.500" 返回 3
        return len(decimal_part)
    
    def _calculate_market_price(self, base_price_str: str, is_buy: bool) -> str:
        """
        计算市价单价格（上下浮动1%）
        
        Args:
            base_price_str: 基准价格字符串（如 "10.50"）
            is_buy: True 为买入（比基准价高1%），False 为卖出（比基准价低1%）
            
        Returns:
            格式化后的价格字符串，使用round对齐小数位
        """
        try:
            base_price = float(base_price_str)
        except ValueError:
            self.logger.error(f"无法解析基准价格: {base_price_str}")
            return base_price_str
        
        # 获取原始价格的小数位数
        decimal_places = self._get_price_decimal_places(base_price_str)
        
        if is_buy:
            # 买入：比基准价高1%
            market_price = base_price * 1.01
        else:
            # 卖出：比基准价低1%
            market_price = base_price * 0.99
            # 确保价格不为负
            if market_price < 0:
                market_price = 0.01
        
        # 使用round对齐小数位
        market_price = round(market_price, decimal_places)
        
        # 格式化为字符串，保持指定的小数位数
        if decimal_places == 0:
            return str(int(market_price))
        else:
            return f"{market_price:.{decimal_places}f}"
    
    def _is_trading_time(self) -> Tuple[bool, str]:
        """
        检查当前是否为交易时间（北京时间 9:25 - 15:00）
        
        Returns:
            (是否在交易时间内, 提示信息)
        """
        # 获取北京时间
        beijing_tz = timezone(timedelta(hours=8))
        beijing_time = datetime.now(beijing_tz)
        current_time = beijing_time.time()
        current_weekday = beijing_time.weekday()  # 0=Monday, 6=Sunday
        
        # 检查是否为周末
        if current_weekday >= 5:  # 周六或周日
            return False, f"当前为周末（{beijing_time.strftime('%Y-%m-%d %H:%M:%S')}），不在交易时间内"
        
        # 交易时间：9:25 - 15:00
        trading_start = dt_time(9, 25)
        trading_end = dt_time(15, 0)
        
        if trading_start <= current_time <= trading_end:
            return True, f"当前时间 {beijing_time.strftime('%Y-%m-%d %H:%M:%S')} 在交易时间内"
        else:
            if current_time < trading_start:
                return False, f"当前时间 {beijing_time.strftime('%Y-%m-%d %H:%M:%S')} 早于交易时间（交易时间：9:25-15:00）"
            else:
                return False, f"当前时间 {beijing_time.strftime('%Y-%m-%d %H:%M:%S')} 晚于交易时间（交易时间：9:25-15:00）"
    

    # @FIX：新增了市价单模式，后期需要整合DataEngine进来
    def press_f1_buy(self, stock_code_or_name: Optional[str] = None, 
                     price: Optional[str] = None, 
                     quantity: Optional[str] = None,
                     price_mode: str = "limit") -> bool:
        """
        按 F1 键 - 买入
        注意：只能在交易时间内执行（北京时间 9:25 - 15:00）
        
        Args:
            stock_code_or_name: 股票代码或名称（可选）
            price: 价格（可选，限价模式下使用指定价格，市价模式下作为基准价格）
            quantity: 数量（可选）
            price_mode: 价格模式，"limit" 为限价单（使用指定价格），"market" 为市价单（比基准价高1%）
        
        Returns:
            是否成功
        """
        # 检查交易时间
        is_trading, message = self._is_trading_time()
        if not is_trading:
            self.logger.error(f"买入操作失败: {message}")
            return False
        
        self.logger.info(f"执行: F1 买入 (价格模式: {price_mode})")
        
        # DEBUG: 有时候多按了个enter之后，如果继续买入，光标会停留在第二第三行，从而逻辑错误，所以买卖切，自动回正。
                    
        # 1. 按 F2 键
        if not self._send_key(0x71, wait_time=0.2):  # VK_F2
            return False
        
        # 1. 按 F1 键
        if not self._send_key(0x70, wait_time=0.2):  # VK_F1
            return False
        
        # 如果没有提供参数，只按 F1 就返回
        if not stock_code_or_name:
            return True
        
        # 2. 连续六次删除（清空输入框）
        self.logger.debug("  清空输入框...")
        if not self._send_backspace(times=6, wait_time=0.1):
            return False
        
        time.sleep(0.3)  # 删除后等待，确保清空完成
        
        # 3. 输入股票代码（通过转换字典）
        stock_code = self._get_stock_code(stock_code_or_name)
        self.logger.info(f"  输入股票代码: {stock_code}")
        if not self._send_text(stock_code, wait_time=0.15):
            return False
        time.sleep(0.2)  # 输入代码后等待
        if not self._send_enter(times=1, wait_time=0.2):
            return False
        time.sleep(0.3)  # Enter 后等待界面切换
        
        # 4. 处理价格（限价或市价）
        final_price = None
        if price_mode == "market" and price:
            # 市价单：计算买入价格（比基准价高1%）
            final_price = self._calculate_market_price(price, is_buy=True)
            self.logger.info(f"  市价单：基准价格 {price}，买入价格 {final_price}")
        elif price:
            # 限价单：使用指定价格
            final_price = price
            self.logger.info(f"  限价单：使用指定价格 {final_price}")
        
        # 5. 输入价格
        if final_price:
            self.logger.info(f"  输入价格: {final_price}")
            if not self._send_text(str(final_price), wait_time=0.15):
                return False
            time.sleep(0.2)  # 输入价格后等待
            if not self._send_enter(times=1, wait_time=0.2):
                return False
            time.sleep(0.3)  # Enter 后等待界面切换
        else:
            # 如果没有提供价格，也要按一次 Enter（跳过价格输入）
            self._send_enter(times=1, wait_time=0.2)
            time.sleep(0.3)
        
        # 6. 输入数量
        if quantity:
            self.logger.info(f"  输入数量: {quantity}")
            if not self._send_text(str(quantity), wait_time=0.15):
                return False
            time.sleep(0.2)  # 输入数量后等待
            if not self._send_enter(times=1, wait_time=0.2):
                return False
            time.sleep(0.3)  # Enter 后等待界面切换
        else:
            # 如果没有提供数量，也要按一次 Enter（跳过数量输入）
            self._send_enter(times=1, wait_time=0.2)
            time.sleep(0.3)
        
        # 7. 全部输入完毕后连续两次 Enter（确认买入）
        self.logger.info("  确认买入...")
        time.sleep(0.2)  # 确认前等待
        if not self._send_enter(times=2, wait_time=0.25):
            return False
        
        self.logger.info("买入操作完成")
        return True
    
    def press_f2_sell(self, stock_code_or_name: Optional[str] = None, 
                     price: Optional[str] = None, 
                     quantity: Optional[str] = None,
                     price_mode: str = "limit") -> bool:
        """
        按 F2 键 - 卖出
        注意：只能在交易时间内执行（北京时间 9:25 - 15:00）
        
        Args:
            stock_code_or_name: 股票代码或名称（可选）
            price: 价格（可选，限价模式下使用指定价格，市价模式下作为基准价格）
            quantity: 数量（可选）
            price_mode: 价格模式，"limit" 为限价单（使用指定价格），"market" 为市价单（比基准价低1%）
        
        Returns:
            是否成功
        """
        # 检查交易时间
        is_trading, message = self._is_trading_time()
        if not is_trading:
            self.logger.error(f"卖出操作失败: {message}")
            return False
        
        self.logger.info(f"执行: F2 卖出 (价格模式: {price_mode})")
        
                # 1. 按 F1 键
        if not self._send_key(0x70, wait_time=0.2):  # VK_F1
            return False

        # 1. 按 F2 键
        if not self._send_key(0x71, wait_time=0.2):  # VK_F2
            return False
        
        # 如果没有提供参数，只按 F2 就返回
        if not stock_code_or_name:
            return True
        
        # 2. 连续六次删除（清空输入框）
        self.logger.debug("  清空输入框...")
        if not self._send_backspace(times=6, wait_time=0.1):
            return False
        
        time.sleep(0.3)  # 删除后等待，确保清空完成
        
        # 3. 输入股票代码（通过转换字典）
        stock_code = self._get_stock_code(stock_code_or_name)
        self.logger.info(f"  输入股票代码: {stock_code}")
        if not self._send_text(stock_code, wait_time=0.15):
            return False
        time.sleep(0.2)  # 输入代码后等待
        if not self._send_enter(times=1, wait_time=0.2):
            return False
        time.sleep(0.3)  # Enter 后等待界面切换
        
        # 4. 处理价格（限价或市价）
        final_price = None
        if price_mode == "market" and price:
            # 市价单：计算卖出价格（比基准价低1%）
            final_price = self._calculate_market_price(price, is_buy=False)
            self.logger.info(f"  市价单：基准价格 {price}，卖出价格 {final_price}")
        elif price:
            # 限价单：使用指定价格
            final_price = price
            self.logger.info(f"  限价单：使用指定价格 {final_price}")
        
        # 5. 输入价格
        if final_price:
            self.logger.info(f"  输入价格: {final_price}")
            if not self._send_text(str(final_price), wait_time=0.4):
                return False
            time.sleep(0.2)  # 输入价格后等待
            if not self._send_enter(times=1, wait_time=0.4):
                return False
            time.sleep(0.3)  # Enter 后等待界面切换
        else:
            # 如果没有提供价格，也要按一次 Enter（跳过价格输入）
            self._send_enter(times=1, wait_time=0.2)
            time.sleep(0.3)
        
        # 6. 输入数量
        if quantity:
            self.logger.info(f"  输入数量: {quantity}")
            if not self._send_text(str(quantity), wait_time=0.15):
                return False
            time.sleep(0.2)  # 输入数量后等待
            if not self._send_enter(times=1, wait_time=0.2):
                return False
            time.sleep(0.3)  # Enter 后等待界面切换
        else:
            # 如果没有提供数量，也要按一次 Enter（跳过数量输入）
            self._send_enter(times=1, wait_time=0.2)
            time.sleep(0.3)
        
        # DEBUG: 有时候卖出之后会卡在确认委托那里，到交易设置里面去取消掉那些确认、或者委托提示之类的东西！
        # 7. 全部输入完毕后连续两次 Enter（确认卖出）
        self.logger.info("  确认卖出...")
        time.sleep(1)  # 确认前等待
        if not self._send_enter(times=2, wait_time=0.3):
            return False
        
        self.logger.info("卖出操作完成")
        return True
    
    def press_f3_cancel(self) -> bool:
        """
        按 F3 键 - 撤单
        
        Returns:
            是否成功
        """
        self.logger.info("执行: F3 撤单")
        result = self._send_key(0x72, wait_time=0.2)  # VK_F3
        # TODO: 后续补充撤单操作逻辑
        return result
    
    def press_f4_query(self, use_vlm: bool = True) -> Optional[Dict[str, Any]]:
        """
        按 F4 键 - 查询资产
        会截图并使用 VLM 分析提取资产数据
        
        Args:
            use_vlm: 是否使用 VLM 分析，默认为 True
        
        Returns:
            如果使用 VLM，返回解析后的资产数据字典；否则返回 None
            字典格式示例：
            {
                "total_assets": "总资产金额",
                "available_cash": "可用资金",
                "market_value": "市值",
                "stocks": [
                    {
                        "code": "股票代码",
                        "name": "股票名称",
                        "quantity": "持仓数量",
                        "cost_price": "成本价",
                        "current_price": "当前价",
                        "market_value": "市值",
                        "profit_loss": "盈亏",
                        "profit_loss_rate": "盈亏比例"
                    }
                ]
            }
        """
        self.logger.info("执行: F4 查询资产")
        
        # 1. 按 F4 键进入资产页面
        if not self._send_key(0x73, wait_time=0.5):  # VK_F4，等待时间稍长确保页面加载
            return None
        
        # 2. 等待页面完全加载
        time.sleep(1.0)
        
        # 3. 截图
        self.logger.info("  正在截图...")
        screenshot = self.capture_window()
        if not screenshot:
            self.logger.error("  截图失败")
            return None
        
        # 获取截图路径（capture_window 会保存截图）
        screenshot_path = self.logger.get_screenshot_path()
        
        # 4. 使用 VLM 分析截图
        if use_vlm and self.vlm_analyzer:
            self.logger.info("  正在使用 VLM 分析资产数据...")
            try:
                # 设计 prompt 来提取资产数据
                prompt = """请仔细分析这张股票交易软件的资产查询页面截图，提取所有资产相关信息。

请以 JSON 格式返回数据，包含以下字段：
1. total_assets: 总资产（字符串，如 "100000.00"）
2. available_cash: 可用资金/可用余额（字符串）
3. market_value: 总市值（字符串）
4. frozen_amount: 冻结资金（字符串，如果有）
5. stocks: 持仓股票列表（数组），每个股票包含：
   - code: 股票代码（字符串，如 "000001"）
   - name: 股票名称（字符串，如 "平安银行"）
   - quantity: 持仓数量（字符串，如 "1000"）
   - cost_price: 成本价（字符串，如 "10.50"）
   - current_price: 当前价/现价（字符串，如 "11.20"）
   - market_value: 市值（字符串，如 "11200.00"）
   - profit_loss: 盈亏金额（字符串，如 "+700.00" 或 "-200.00"）
   - profit_loss_rate: 盈亏比例（字符串，如 "+6.67%" 或 "-1.90%"）

要求：
- 如果某个字段在截图中找不到，请设置为空字符串 "" 或空数组 []
- 所有数字字段都保持为字符串格式，不要转换为数字
- 确保提取的数据准确，特别是股票代码、名称、数量、价格等关键信息
- 如果截图中没有显示资产信息或页面未加载完成，返回空数据

请直接返回 JSON 格式，不要包含其他说明文字。"""

                # 调用 VLM 分析
                result = self.vlm_analyzer.analyze_json(
                    image_path=screenshot_path,
                    prompt=prompt
                )
                
                self.logger.info("  VLM 分析完成")
                
                # 尝试解析和格式化返回结果
                if isinstance(result, dict):
                    # 如果返回的是字典，直接返回
                    return result
                elif isinstance(result, str):
                    # 如果返回的是字符串，尝试解析 JSON
                    try:
                        return json.loads(result)
                    except json.JSONDecodeError:
                        self.logger.warning(f"  VLM 返回的不是有效 JSON: {result}")
                        return {"raw_result": result}
                else:
                    return {"result": result}
                    
            except Exception as e:
                self.logger.error(f"  VLM 分析失败: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                return None
        else:
            self.logger.warning("  未使用 VLM 分析（VLM 不可用或已禁用）")
            return None
    
    def press_f6_position(self) -> bool:
        """
        按 F6 键 - 持仓
        注意：会先按一次 F1(买入) 进入买入界面，然后按 F6 跳转到持仓
        
        Returns:
            是否成功
        """
        self.logger.info("执行: F1 -> F6 持仓")
        # 先按 F1 进入买入界面
        if not self.press_f1_buy():
            return False
        time.sleep(0.3)  # 等待界面切换
        # 再按 F6 跳转到持仓
        result = self._send_key(0x75, wait_time=0.2)  # VK_F6
        # TODO: 后续补充持仓查询操作逻辑
        return result
    
    def press_f7_filled_orders(self) -> bool:
        """
        按 F7 键 - 成交单
        注意：会先按一次 F1(买入) 进入买入界面，然后按 F7 跳转到成交单
        
        Returns:
            是否成功
        """
        self.logger.info("执行: F1 -> F7 成交单")
        # 先按 F1 进入买入界面
        if not self.press_f1_buy():
            return False
        time.sleep(0.3)  # 等待界面切换
        # 再按 F7 跳转到成交单
        result = self._send_key(0x76, wait_time=0.2)  # VK_F7
        # TODO: 后续补充成交单查询操作逻辑
        return result
    
    def press_f8_pending_orders(self) -> bool:
        """
        按 F8 键 - 委托单
        注意：会先按一次 F1(买入) 进入买入界面，然后按 F8 跳转到委托单
        
        Returns:
            是否成功
        """
        self.logger.info("执行: F1 -> F8 委托单")
        # 先按 F1 进入买入界面
        if not self.press_f1_buy():
            return False
        time.sleep(0.3)  # 等待界面切换
        # 再按 F8 跳转到委托单
        result = self._send_key(0x77, wait_time=0.2)  # VK_F8
        # TODO: 后续补充委托单查询操作逻辑
        return result


def test_buy_sell(executor: TongHuaShunExecutor, 
                  stock_code: str = "000001", 
                  price: str = "10.00", 
                  quantity: str = "100"):
    """
    测试买入和卖出功能
    
    Args:
        executor: TongHuaShunExecutor 实例
        stock_code: 股票代码（默认：000001）
        price: 价格（默认：10.00）
        quantity: 数量（默认：100）
    """
    print("\n" + "="*50)
    print("开始测试买入卖出功能")
    print("="*50)
    
    # 测试买入
    print("\n【测试1】买入操作")
    print(f"股票代码: {stock_code}, 价格: {price}, 数量: {quantity}")
    if executor.press_f1_buy(stock_code_or_name=stock_code, price=price, quantity=quantity):
        print("✓ 买入操作执行成功")
    else:
        print("✗ 买入操作执行失败")
    
    # 等待操作完成
    time.sleep(2)
    
    # 测试卖出
    print("\n【测试2】卖出操作")
    print(f"股票代码: {stock_code}, 价格: {price}, 数量: {quantity}")
    if executor.press_f2_sell(stock_code_or_name=stock_code, price=price, quantity=quantity):
        print("✓ 卖出操作执行成功")
    else:
        print("✗ 卖出操作执行失败")
    
    # 等待操作完成
    time.sleep(2)
    
    # 测试查看持仓（F1 -> F6）
    print("\n【测试3】查看持仓（F1 -> F6）")
    if executor.press_f6_position():
        print("✓ 查看持仓操作执行成功")
    else:
        print("✗ 查看持仓操作执行失败")
    
    time.sleep(2)
    
    # 测试查看成交单（F1 -> F7）
    print("\n【测试4】查看成交单（F1 -> F7）")
    if executor.press_f7_filled_orders():
        print("✓ 查看成交单操作执行成功")
    else:
        print("✗ 查看成交单操作执行失败")
    
    time.sleep(2)
    
    # 测试查看委托单（F1 -> F8）
    print("\n【测试5】查看委托单（F1 -> F8）")
    if executor.press_f8_pending_orders():
        print("✓ 查看委托单操作执行成功")
    else:
        print("✗ 查看委托单操作执行失败")
    
    print("\n" + "="*50)
    print("测试完成")
    print("="*50 + "\n")


def test_f4_query(executor: TongHuaShunExecutor):
    """
    测试 F4 查询资产功能
    
    Args:
        executor: TongHuaShunExecutor 实例
    """
    print("\n" + "="*50)
    print("开始测试 F4 查询资产功能")
    print("="*50)
    
    # 测试 F4 查询
    print("\n【测试】F4 查询资产（使用 VLM 分析）")
    asset_data = executor.press_f4_query(use_vlm=True)
    
    if asset_data:
        print("\n✓ 资产数据提取成功")
        print("\n=== 资产概览 ===")
        
        # 显示总资产信息
        if asset_data.get("total_assets"):
            print(f"总资产: {asset_data.get('total_assets')}")
        if asset_data.get("available_cash"):
            print(f"可用资金: {asset_data.get('available_cash')}")
        if asset_data.get("market_value"):
            print(f"总市值: {asset_data.get('market_value')}")
        if asset_data.get("frozen_amount"):
            print(f"冻结资金: {asset_data.get('frozen_amount')}")
        
        # 显示持仓股票
        stocks = asset_data.get("stocks", [])
        if stocks:
            print(f"\n=== 持仓股票 (共 {len(stocks)} 只) ===")
            for i, stock in enumerate(stocks, 1):
                print(f"\n【{i}】{stock.get('name', '未知')} ({stock.get('code', '未知')})")
                if stock.get('quantity'):
                    print(f"  持仓数量: {stock.get('quantity')}")
                if stock.get('cost_price'):
                    print(f"  成本价: {stock.get('cost_price')}")
                if stock.get('current_price'):
                    print(f"  当前价: {stock.get('current_price')}")
                if stock.get('market_value'):
                    print(f"  市值: {stock.get('market_value')}")
                if stock.get('profit_loss'):
                    print(f"  盈亏: {stock.get('profit_loss')}")
                if stock.get('profit_loss_rate'):
                    print(f"  盈亏比例: {stock.get('profit_loss_rate')}")
        else:
            print("\n无持仓股票")
        
        # 保存结果到 JSON 文件
        try:
            result_file = executor.logger.save_asset_data(asset_data)
            print(f"\n✓ 资产数据已保存到: {result_file}")
        except Exception as e:
            print(f"\n✗ 保存资产数据失败: {e}")
        
        # 返回完整数据供进一步处理
        return asset_data
    else:
        print("\n✗ 资产数据提取失败")
        return None
    
    print("\n" + "="*50)
    print("F4 查询测试完成")
    print("="*50 + "\n")


if __name__ == '__main__':
    """
    测试示例
    """
    # 示例：创建执行器
    exe_path = r"D:\Program Files (x86)\ths\同花顺\xiadan.exe"  # 请修改为实际路径
    executor = TongHuaShunExecutor(exe_path)
    
    # 维护股票代码转换字典（可选）
    executor.stock_name_to_code = {
        '平安银行': '000001',
        '万科A': '000002',
        '国农科技': '000004',
        # 可以继续添加更多股票映射
    }
    
    # 方式1: 启动新程序
    if executor.launch_program():
        print("程序启动成功")
        # 等待程序完全加载
        time.sleep(3)
        
        # 测试 F4 查询资产功能
        print("\n" + "="*60)
        print("开始测试 F4 查询资产功能")
        print("="*60)
        asset_data = test_f4_query(executor)
        
        if asset_data:
            print("\n✓ F4 查询测试成功完成")
        else:
            print("\n✗ F4 查询测试失败")
        
        # 可选：运行买入卖出测试（取消注释以启用）
        # print("\n" + "="*60)
        # print("开始测试买入卖出功能")
        # print("="*60)
        # test_buy_sell(
        #     executor=executor,
        #     stock_code="000001",  # 测试股票代码
        #     price="10.00",        # 测试价格
        #     quantity="100"        # 测试数量
        # )
    
    # 方式2: 激活已运行的程序（取消注释以使用）
    elif executor.activate_window():
        print("窗口激活成功")
        time.sleep(1)
        
        # 测试 F4 查询资产功能
        print("\n" + "="*60)
        print("开始测试 F4 查询资产功能")
        print("="*60)
        asset_data = test_f4_query(executor)
        
        if asset_data:
            print("\n✓ F4 查询测试成功完成")
        else:
            print("\n✗ F4 查询测试失败")
        
        # 可选：运行买入卖出测试（取消注释以启用）
        # print("\n" + "="*60)
        # print("开始测试买入卖出功能")
        # print("="*60)
        # test_buy_sell(
        #     executor=executor,
        #     stock_code="000001",
        #     price="10.00",
        #     quantity="100"
        # )
    else:
        print("无法启动或激活程序，请检查程序路径或确保程序已运行")

