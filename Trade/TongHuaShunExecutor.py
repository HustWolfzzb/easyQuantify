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
from typing import Dict, Tuple, Optional, List, Any
from datetime import datetime
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
    from Trade.VLMImageAnalyzer import VLMImageAnalyzer
    VLM_AVAILABLE = True
except ImportError:
    VLM_AVAILABLE = False
    print("警告: VLMImageAnalyzer 未安装，F4 查询功能将无法使用 VLM 分析")

# OCR 库检测（延迟导入，避免导入时失败）
OCR_TYPE = None
OCR_AVAILABLE = False

def _check_ocr_availability():
    """检查可用的 OCR 库（延迟检查，避免导入时失败）"""
    global OCR_TYPE, OCR_AVAILABLE
    
    if OCR_AVAILABLE:
        return OCR_TYPE
    
    # 优先尝试 easyocr
    try:
        import easyocr
        OCR_TYPE = 'easyocr'
        OCR_AVAILABLE = True
        return 'easyocr'
    except (ImportError, OSError, Exception) as e:
        # OSError 可能包含 DLL 加载错误
        pass
    
    # 尝试 pytesseract (Tesseract OCR，更轻量级)
    try:
        import pytesseract
        from PIL import Image
        OCR_TYPE = 'pytesseract'
        OCR_AVAILABLE = True
        return 'pytesseract'
    except ImportError:
        pass
    
    # 尝试百度 OCR
    try:
        from aip import AipOcr
        OCR_TYPE = 'baidu'
        OCR_AVAILABLE = True
        return 'baidu'
    except ImportError:
        pass
    
    OCR_AVAILABLE = False
    return None

# 初始化时检查 OCR 可用性
_check_ocr_availability()
if OCR_TYPE:
    print(f"检测到 OCR 库: {OCR_TYPE}")
else:
    print("警告: 未安装 OCR 库，将使用基础图像识别")
    print("建议安装以下之一:")
    print("  1. pip install pytesseract  (需要先安装 Tesseract OCR)")
    print("  2. pip install easyocr  (需要 PyTorch，可能遇到 DLL 问题)")
    print("  3. pip install baidu-aip  (需要百度 API 密钥)")


class TongHuaShunExecutor:
    """
    同花顺执行器类
    通过 Windows 窗口操作和图像识别来控制 xiadan.exe 程序
    """
    
    def __init__(self, exe_path: str, screenshot_dir: str = "screenshots", 
                 ocr_app_id: Optional[str] = None, 
                 ocr_api_key: Optional[str] = None, 
                 ocr_secret_key: Optional[str] = None):
        """
        初始化执行器
        
        Args:
            exe_path: xiadan.exe 程序的完整路径
            screenshot_dir: 截图保存目录
            ocr_app_id: 百度 OCR App ID（可选）
            ocr_api_key: 百度 OCR API Key（可选）
            ocr_secret_key: 百度 OCR Secret Key（可选）
        """
        self.exe_path = exe_path
        self.screenshot_dir = screenshot_dir
        self.hwnd = None  # 窗口句柄
        self.window_rect = None  # 窗口坐标 (left, top, right, bottom)
        
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
                print("VLM 分析器初始化成功")
            except Exception as e:
                print(f"VLM 分析器初始化失败: {e}")
                self.vlm_analyzer = None
        
        # 创建截图目录
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)
        
        # 初始化 OCR（延迟初始化，避免导入时失败）
        self.ocr_client = None
        self.ocr_type = _check_ocr_availability()
        
        if self.ocr_type == 'easyocr':
            try:
                import easyocr
                # easyocr 支持中文和英文
                print("正在初始化本地 OCR (easyocr)，首次运行会下载模型，请稍候...")
                self.ocr_client = easyocr.Reader(['ch_sim', 'en'], gpu=False)  # 中文简体和英文
                print("本地 OCR 初始化成功")
            except Exception as e:
                print(f"本地 OCR 初始化失败: {e}")
                print("提示: 如果遇到 DLL 错误，可以尝试:")
                print("  1. 安装 Visual C++ Redistributable")
                print("  2. 重新安装 PyTorch: pip install torch --index-url https://download.pytorch.org/whl/cu118")
                print("  3. 或使用 pytesseract 作为替代方案")
                self.ocr_client = None
                self.ocr_type = None
        elif self.ocr_type == 'pytesseract':
            try:
                import pytesseract
                self.ocr_client = pytesseract
                # 设置 Tesseract 路径（如果需要）
                # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                print("Tesseract OCR 初始化成功")
            except Exception as e:
                print(f"Tesseract OCR 初始化失败: {e}")
                print("提示: 需要先安装 Tesseract OCR:")
                print("  下载地址: https://github.com/UB-Mannheim/tesseract/wiki")
                self.ocr_client = None
                self.ocr_type = None
        elif self.ocr_type == 'baidu' and ocr_app_id and ocr_api_key and ocr_secret_key:
            try:
                from aip import AipOcr
                self.ocr_client = AipOcr(ocr_app_id, ocr_api_key, ocr_secret_key)
                print("百度 OCR 初始化成功")
            except Exception as e:
                print(f"百度 OCR 初始化失败: {e}")
                self.ocr_client = None
                self.ocr_type = None
        
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
            # 打印所有找到的窗口信息
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
    
    def get_window_rect(self, hwnd: int) -> Tuple[int, int, int, int]:
        """
        获取窗口坐标（客户区，不包括标题栏和边框）
        
        Args:
            hwnd: 窗口句柄
            
        Returns:
            (left, top, right, bottom) 窗口客户区坐标（屏幕坐标）
        """
        try:
            # 检查窗口是否有效
            if not win32gui.IsWindow(hwnd):
                raise ValueError("窗口句柄无效")
            
            # 获取客户区矩形（相对于窗口）
            # GetClientRect 返回 (left, top, right, bottom)，其中 left 和 top 通常是 0
            client_rect = win32gui.GetClientRect(hwnd)
            client_left, client_top, client_right, client_bottom = client_rect
            
            # 将客户区左上角坐标转换为屏幕坐标
            screen_left, screen_top = win32gui.ClientToScreen(hwnd, (client_left, client_top))
            
            # 将客户区右下角坐标转换为屏幕坐标
            screen_right, screen_bottom = win32gui.ClientToScreen(hwnd, (client_right, client_bottom))
            
            return (screen_left, screen_top, screen_right, screen_bottom)
        except Exception as e:
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
            print(f"聚焦窗口时出错: {e}")
            return False
    
    def launch_program(self) -> bool:
        """
        启动 xiadan.exe 程序
        
        Returns:
            是否成功启动
        """
        if not os.path.exists(self.exe_path):
            print(f"程序路径不存在: {self.exe_path}")
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
                print(f"程序启动成功")
                print(f"  窗口句柄: {self.hwnd}")
                print(f"  窗口标题: '{window_title}'")
                print(f"  窗口类名: '{window_class}'")
                print(f"  客户区坐标: {self.window_rect}")
                print(f"  客户区尺寸: {width}x{height}")
                return True
            else:
                print("无法找到程序窗口")
                return False
        except Exception as e:
            print(f"启动程序失败: {e}")
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
                print(f"窗口激活成功")
                print(f"  窗口句柄: {self.hwnd}")
                print(f"  窗口标题: '{window_title}'")
                print(f"  窗口类名: '{window_class}'")
                print(f"  客户区坐标: {self.window_rect}")
                print(f"  客户区尺寸: {width}x{height}")
                return True
        
        print("无法找到程序窗口，请先启动程序")
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
            print("窗口未激活，请先启动或激活程序")
            return None
        
        try:
            # 聚焦窗口，确保窗口在前台
            if not self.focus_window(self.hwnd):
                print("无法聚焦窗口，尝试继续...")
            
            time.sleep(0.2)  # 等待窗口完全显示
            
            # 重新获取窗口坐标（窗口可能移动了）
            self.window_rect = self.get_window_rect(self.hwnd)
            left, top, right, bottom = self.window_rect
            width = right - left
            height = bottom - top
            
            # 验证窗口尺寸和坐标是否合理
            if width <= 0 or height <= 0:
                print(f"错误: 窗口尺寸无效 ({width}x{height})")
                print(f"坐标: left={left}, top={top}, right={right}, bottom={bottom}")
                # 尝试使用窗口矩形而不是客户区
                try:
                    rect = win32gui.GetWindowRect(self.hwnd)
                    left, top, right, bottom = rect
                    width = right - left
                    height = bottom - top
                    print(f"使用窗口矩形: {width}x{height}")
                    self.window_rect = rect
                except Exception as e:
                    print(f"获取窗口矩形也失败: {e}")
                    return None
            
            if width < 50 or height < 50:
                print(f"警告: 窗口尺寸异常 ({width}x{height})，可能是错误的窗口")
                window_title = win32gui.GetWindowText(self.hwnd)
                print(f"当前窗口标题: '{window_title}'")
                # 即使尺寸异常，也尝试截图
            
            # 确保坐标有效（right > left, bottom > top）
            if right <= left or bottom <= top:
                print(f"错误: 坐标无效 - left={left}, top={top}, right={right}, bottom={bottom}")
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
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = os.path.join(self.screenshot_dir, f"screenshot_{timestamp}.png")
            
            screenshot.save(save_path)
            print(f"截图已保存: {save_path}")
            
            return screenshot
        except Exception as e:
            print(f"截图失败: {e}")
            return None
    
    def _ocr_recognize(self, image: Image.Image) -> List[Dict]:
        """
        使用 OCR 识别图像中的文字
        
        Args:
            image: PIL Image 对象
            
        Returns:
            OCR 识别结果列表，格式统一为: [{'words': '文字', 'location': {'left': x, 'top': y, 'width': w, 'height': h}}, ...]
        """
        if not self.ocr_client or not self.ocr_type:
            return []
        
        try:
            if self.ocr_type == 'easyocr':
                # 使用 easyocr
                # 转换为 numpy 数组
                img_array = np.array(image)
                # easyocr 需要 BGR 格式
                if len(img_array.shape) == 3:
                    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                else:
                    img_bgr = img_array
                
                # 调用 OCR
                results = self.ocr_client.readtext(img_bgr)
                
                # 转换为统一格式
                ocr_results = []
                for result in results:
                    # result 格式: (bbox, text, confidence)
                    # bbox 格式: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                    bbox = result[0]
                    text = result[1]
                    confidence = result[2]
                    
                    # 计算边界框
                    xs = [point[0] for point in bbox]
                    ys = [point[1] for point in bbox]
                    left = int(min(xs))
                    top = int(min(ys))
                    right = int(max(xs))
                    bottom = int(max(ys))
                    width = right - left
                    height = bottom - top
                    
                    # 只保留置信度较高的结果
                    if confidence > 0.3:  # 可以调整阈值
                        ocr_results.append({
                            'words': text,
                            'location': {
                                'left': left,
                                'top': top,
                                'width': width,
                                'height': height
                            },
                            'confidence': confidence
                        })
                
                return ocr_results
                
            elif self.ocr_type == 'pytesseract':
                # 使用 pytesseract (Tesseract OCR)
                # 配置：支持中文和英文
                import pytesseract
                
                # 使用 image_to_data 获取带位置信息的识别结果
                # lang='chi_sim+eng' 表示中文简体和英文
                try:
                    data = pytesseract.image_to_data(image, lang='chi_sim+eng', output_type=pytesseract.Output.DICT)
                except:
                    # 如果中文语言包未安装，只使用英文
                    data = pytesseract.image_to_data(image, lang='eng', output_type=pytesseract.Output.DICT)
                
                ocr_results = []
                n_boxes = len(data['text'])
                
                for i in range(n_boxes):
                    text = data['text'][i].strip()
                    conf = int(data['conf'][i])
                    
                    # 过滤空文本和低置信度结果
                    if text and conf > 30:  # 置信度阈值
                        left = data['left'][i]
                        top = data['top'][i]
                        width = data['width'][i]
                        height = data['height'][i]
                        
                        ocr_results.append({
                            'words': text,
                            'location': {
                                'left': left,
                                'top': top,
                                'width': width,
                                'height': height
                            },
                            'confidence': conf / 100.0  # 转换为 0-1 范围
                        })
                
                return ocr_results
                
            elif self.ocr_type == 'baidu':
                # 使用百度 OCR
                # 将图像转换为字节
                img_bytes = io.BytesIO()
                image.save(img_bytes, format='PNG')
                img_bytes = img_bytes.getvalue()
                
                # 调用 OCR
                options = {"recognize_granularity": "small"}
                result = self.ocr_client.general(img_bytes, options)
                
                if 'words_result' in result:
                    return result['words_result']
        except Exception as e:
            print(f"OCR 识别失败: {e}")
            import traceback
            traceback.print_exc()
        
        return []
    
    def detect_buttons(self, image: Image.Image) -> Dict[str, Tuple[int, int]]:
        """
        识别图像中的按钮并返回中心坐标
        
        Args:
            image: PIL Image 对象
            
        Returns:
            字典，格式为 {按钮名称: (中心x, 中心y)}
        """
        # 转换为 OpenCV 格式
        img_array = np.array(image)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        img_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        buttons = {}
        
        # 获取图像尺寸
        img_height, img_width = img_gray.shape
        print(f"图像尺寸: {img_width}x{img_height}")
        
        # 方法1: 使用轮廓检测识别按钮（矩形区域）
        # 二值化
        _, binary = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        print(f"找到 {len(contours)} 个轮廓")
        
        # 获取 OCR 识别结果（用于识别按钮文字）
        ocr_results = self._ocr_recognize(image) if self.ocr_client else []
        if ocr_results:
            print(f"OCR 识别到 {len(ocr_results)} 个文字区域")
        
        # 过滤出可能是按钮的矩形区域
        button_index = 1
        min_area = max(100, img_width * img_height * 0.001)  # 动态调整最小面积
        print(f"按钮识别参数: 最小面积={min_area:.0f}, 最小高度=15")
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            # 过滤太小的区域
            if area < min_area:
                continue
            
            # 获取边界矩形
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / float(h) if h > 0 else 0
            
            # 按钮通常是横向或接近正方形的矩形，放宽条件
            if 0.3 < aspect_ratio < 5.0 and h > 15 and w > 20:  # 放宽条件
                center_x = x + w // 2
                center_y = y + h // 2
                
                # 尝试通过 OCR 识别按钮文字
                button_name = None
                if ocr_results:
                    for ocr_item in ocr_results:
                        if 'location' in ocr_item:
                            loc = ocr_item['location']
                            # 检查 OCR 文字是否在按钮区域内
                            ocr_left = loc.get('left', 0)
                            ocr_top = loc.get('top', 0)
                            ocr_width = loc.get('width', 0)
                            ocr_height = loc.get('height', 0)
                            
                            # 判断 OCR 文字中心是否在按钮区域内
                            ocr_center_x = ocr_left + ocr_width // 2
                            ocr_center_y = ocr_top + ocr_height // 2
                            
                            if (x <= ocr_center_x <= x + w and 
                                y <= ocr_center_y <= y + h):
                                button_name = ocr_item.get('words', '').strip()
                                if button_name:
                                    break
                
                # 如果没有识别到文字，使用默认名称
                if not button_name:
                    button_name = f"按钮_{button_index}"
                    button_index += 1
                
                buttons[button_name] = (center_x, center_y)
                print(f"检测到按钮: {button_name} 中心坐标: ({center_x}, {center_y}), 尺寸: {w}x{h}, 面积: {area:.0f}")
        
        return buttons
    
    def detect_input_boxes(self, image: Image.Image) -> Dict[str, Tuple[int, int]]:
        """
        识别图像中的输入框并返回中心坐标
        
        Args:
            image: PIL Image 对象
            
        Returns:
            字典，格式为 {输入框名称: (中心x, 中心y)}
        """
        # 转换为 OpenCV 格式
        img_array = np.array(image)
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        img_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        input_boxes = {}
        
        # 获取图像尺寸
        img_height, img_width = img_gray.shape
        
        # 方法1: 使用边缘检测识别输入框
        edges = cv2.Canny(img_gray, 50, 150)
        
        # 查找轮廓
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        print(f"输入框检测: 找到 {len(contours)} 个边缘轮廓")
        
        # 获取 OCR 识别结果（用于识别输入框标签）
        ocr_results = self._ocr_recognize(image) if self.ocr_client else []
        if ocr_results:
            print(f"输入框 OCR 识别到 {len(ocr_results)} 个文字区域")
            # 打印所有识别到的文字（用于调试）
            for ocr_item in ocr_results:
                words = ocr_item.get('words', '').strip()
                if words:
                    loc = ocr_item.get('location', {})
                    print(f"  OCR文字: '{words}' 位置: ({loc.get('left', 0)}, {loc.get('top', 0)})")
        
        # 过滤出可能是输入框的矩形区域
        input_index = 1
        min_area = max(50, img_width * img_height * 0.0005)  # 动态调整最小面积
        print(f"输入框识别参数: 最小面积={min_area:.0f}, 高度范围=10-60")
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            # 过滤太小的区域
            if area < min_area:
                continue
            
            # 获取边界矩形
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / float(h) if h > 0 else 0
            
            # 输入框通常是横向的矩形，放宽条件
            if aspect_ratio > 1.5 and h > 10 and h < 60 and w > 30:  # 放宽条件
                center_x = x + w // 2
                center_y = y + h // 2
                
                # 尝试通过 OCR 识别输入框标签（通常在输入框左侧或上方）
                input_name = None
                best_match = None
                min_distance = float('inf')
                
                if ocr_results:
                    # 查找输入框附近的文字标签
                    for ocr_item in ocr_results:
                        if 'location' in ocr_item:
                            loc = ocr_item['location']
                            ocr_left = loc.get('left', 0)
                            ocr_top = loc.get('top', 0)
                            ocr_width = loc.get('width', 0)
                            ocr_height = loc.get('height', 0)
                            ocr_right = ocr_left + ocr_width
                            ocr_bottom = ocr_top + ocr_height
                            
                            # 计算文字中心
                            ocr_center_x = ocr_left + ocr_width // 2
                            ocr_center_y = ocr_top + ocr_height // 2
                            
                            words = ocr_item.get('words', '').strip()
                            if not words:
                                continue
                            
                            # 检查文字是否在输入框附近（左侧、上方或内部）
                            # 左侧：文字在输入框左侧，且垂直对齐
                            is_left = (ocr_right < x + 50 and 
                                      abs(ocr_center_y - center_y) < h + 15)
                            
                            # 上方：文字在输入框上方，且水平对齐
                            is_above = (ocr_bottom < y + 20 and 
                                       abs(ocr_center_x - center_x) < w + 20)
                            
                            # 内部：文字在输入框内部（可能是占位符）
                            is_inside = (x <= ocr_center_x <= x + w and 
                                        y <= ocr_center_y <= y + h)
                            
                            if is_left or is_above:
                                # 计算距离，选择最近的标签
                                distance = ((ocr_center_x - center_x) ** 2 + 
                                          (ocr_center_y - center_y) ** 2) ** 0.5
                                
                                if distance < min_distance:
                                    min_distance = distance
                                    best_match = words
                            
                            # 如果是内部文字且看起来像标签（短文本，可能是占位符）
                            elif is_inside and len(words) < 10:
                                # 检查是否是常见的占位符关键词
                                placeholder_keywords = ['请输入', '输入', '代码', '价格', '数量']
                                if any(kw in words for kw in placeholder_keywords):
                                    best_match = words
                                    break
                    
                    if best_match:
                        input_name = best_match
                
                # 如果没有识别到标签，使用默认名称
                if not input_name:
                    input_name = f"输入框_{input_index}"
                    input_index += 1
                
                input_boxes[input_name] = (center_x, center_y)
                print(f"检测到输入框: {input_name} 中心坐标: ({center_x}, {center_y}), 尺寸: {w}x{h}, 面积: {area:.0f}")
        
        return input_boxes
    
    def analyze_ui(self, image: Optional[Image.Image] = None) -> Dict[str, Dict[str, Tuple[int, int]]]:
        """
        分析界面，识别所有按钮和输入框
        
        Args:
            image: PIL Image 对象，如果为 None 则自动截图
            
        Returns:
            字典，包含 'buttons' 和 'input_boxes' 两个键
        """
        if image is None:
            image = self.capture_window()
            if image is None:
                return {'buttons': {}, 'input_boxes': {}}
        
        # 识别按钮
        buttons = self.detect_buttons(image)
        
        # 识别输入框
        input_boxes = self.detect_input_boxes(image)
        
        # 更新缓存
        self.ui_elements = {
            'buttons': buttons,
            'input_boxes': input_boxes
        }
        
        return {
            'buttons': buttons,
            'input_boxes': input_boxes
        }
    
    def get_element_coordinate(self, element_name: str, element_type: str = 'auto') -> Optional[Tuple[int, int]]:
        """
        获取界面元素的坐标（相对于窗口）
        
        Args:
            element_name: 元素名称
            element_type: 元素类型 ('button', 'input_box', 'auto')
            
        Returns:
            (x, y) 坐标，如果未找到返回 None
        """
        if not self.ui_elements:
            print("界面元素未识别，请先调用 analyze_ui()")
            return None
        
        # 自动判断类型
        if element_type == 'auto':
            if element_name in self.ui_elements.get('buttons', {}):
                element_type = 'button'
            elif element_name in self.ui_elements.get('input_boxes', {}):
                element_type = 'input_box'
            else:
                print(f"未找到元素: {element_name}")
                return None
        
        # 获取坐标
        if element_type == 'button':
            coord = self.ui_elements.get('buttons', {}).get(element_name)
        elif element_type == 'input_box':
            coord = self.ui_elements.get('input_boxes', {}).get(element_name)
        else:
            print(f"不支持的元素类型: {element_type}")
            return None
        
        if coord:
            # 转换为屏幕绝对坐标
            if self.window_rect:
                screen_x = self.window_rect[0] + coord[0]
                screen_y = self.window_rect[1] + coord[1]
                return (screen_x, screen_y)
            return coord
        
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
            
            print(f"已点击元素: {element_name} 坐标: {coord}")
            return True
        except Exception as e:
            print(f"点击元素失败: {e}")
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
            
            print(f"已在 {element_name} 输入文本: {text}")
            return True
        except Exception as e:
            print(f"输入文本失败: {e}")
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
            print(f"发送按键失败: {e}")
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
            print(f"发送 Backspace 失败: {e}")
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
            print(f"发送 Enter 失败: {e}")
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
                    print(f"警告: 字符 '{char}' 无法直接输入，尝试使用剪贴板方式")
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
                        print(f"剪贴板输入也失败: {e}")
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
            print(f"输入文本失败: {e}")
            import traceback
            traceback.print_exc()
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
        print(f"警告: 未找到股票 '{stock_input}' 的代码映射，使用原输入")
        return stock_input
    
    def press_f1_buy(self, stock_code_or_name: Optional[str] = None, 
                     price: Optional[str] = None, 
                     quantity: Optional[str] = None) -> bool:
        """
        按 F1 键 - 买入
        
        Args:
            stock_code_or_name: 股票代码或名称（可选）
            price: 价格（可选）
            quantity: 数量（可选）
        
        Returns:
            是否成功
        """
        print("执行: F1 买入")
        
        # 1. 按 F1 键
        if not self._send_key(0x70, wait_time=0.2):  # VK_F1
            return False
        
        # 如果没有提供参数，只按 F1 就返回
        if not stock_code_or_name:
            return True
        
        # 2. 连续六次删除（清空输入框）
        print("  清空输入框...")
        if not self._send_backspace(times=6, wait_time=0.1):
            return False
        
        time.sleep(0.3)  # 删除后等待，确保清空完成
        
        # 3. 输入股票代码（通过转换字典）
        stock_code = self._get_stock_code(stock_code_or_name)
        print(f"  输入股票代码: {stock_code}")
        if not self._send_text(stock_code, wait_time=0.15):
            return False
        time.sleep(0.2)  # 输入代码后等待
        if not self._send_enter(times=1, wait_time=0.2):
            return False
        time.sleep(0.3)  # Enter 后等待界面切换
        
        # 4. 输入价格
        if price:
            print(f"  输入价格: {price}")
            if not self._send_text(str(price), wait_time=0.15):
                return False
            time.sleep(0.2)  # 输入价格后等待
            if not self._send_enter(times=1, wait_time=0.2):
                return False
            time.sleep(0.3)  # Enter 后等待界面切换
        else:
            # 如果没有提供价格，也要按一次 Enter（跳过价格输入）
            self._send_enter(times=1, wait_time=0.2)
            time.sleep(0.3)
        
        # 5. 输入数量
        if quantity:
            print(f"  输入数量: {quantity}")
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
        
        # 6. 全部输入完毕后连续两次 Enter（确认买入）
        print("  确认买入...")
        time.sleep(0.2)  # 确认前等待
        if not self._send_enter(times=2, wait_time=0.25):
            return False
        
        print("买入操作完成")
        return True
    
    def press_f2_sell(self, stock_code_or_name: Optional[str] = None, 
                     price: Optional[str] = None, 
                     quantity: Optional[str] = None) -> bool:
        """
        按 F2 键 - 卖出
        
        Args:
            stock_code_or_name: 股票代码或名称（可选）
            price: 价格（可选）
            quantity: 数量（可选）
        
        Returns:
            是否成功
        """
        print("执行: F2 卖出")
        
        # 1. 按 F2 键
        if not self._send_key(0x71, wait_time=0.2):  # VK_F2
            return False
        
        # 如果没有提供参数，只按 F2 就返回
        if not stock_code_or_name:
            return True
        
        # 2. 连续六次删除（清空输入框）
        print("  清空输入框...")
        if not self._send_backspace(times=6, wait_time=0.1):
            return False
        
        time.sleep(0.3)  # 删除后等待，确保清空完成
        
        # 3. 输入股票代码（通过转换字典）
        stock_code = self._get_stock_code(stock_code_or_name)
        print(f"  输入股票代码: {stock_code}")
        if not self._send_text(stock_code, wait_time=0.15):
            return False
        time.sleep(0.2)  # 输入代码后等待
        if not self._send_enter(times=1, wait_time=0.2):
            return False
        time.sleep(0.3)  # Enter 后等待界面切换
        
        # 4. 输入价格
        if price:
            print(f"  输入价格: {price}")
            if not self._send_text(str(price), wait_time=0.15):
                return False
            time.sleep(0.2)  # 输入价格后等待
            if not self._send_enter(times=1, wait_time=0.2):
                return False
            time.sleep(0.3)  # Enter 后等待界面切换
        else:
            # 如果没有提供价格，也要按一次 Enter（跳过价格输入）
            self._send_enter(times=1, wait_time=0.2)
            time.sleep(0.3)
        
        # 5. 输入数量
        if quantity:
            print(f"  输入数量: {quantity}")
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
        
        # 6. 全部输入完毕后连续两次 Enter（确认卖出）
        print("  确认卖出...")
        time.sleep(0.2)  # 确认前等待
        if not self._send_enter(times=2, wait_time=0.25):
            return False
        
        print("卖出操作完成")
        return True
    
    def press_f3_cancel(self) -> bool:
        """
        按 F3 键 - 撤单
        
        Returns:
            是否成功
        """
        print("执行: F3 撤单")
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
        print("执行: F4 查询资产")
        
        # 1. 按 F4 键进入资产页面
        if not self._send_key(0x73, wait_time=0.5):  # VK_F4，等待时间稍长确保页面加载
            return None
        
        # 2. 等待页面完全加载
        time.sleep(1.0)
        
        # 3. 截图
        print("  正在截图...")
        screenshot = self.capture_window()
        if not screenshot:
            print("  截图失败")
            return None
        
        # 获取截图路径（capture_window 会保存截图）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(self.screenshot_dir, f"screenshot_{timestamp}.png")
        
        # 4. 使用 VLM 分析截图
        if use_vlm and self.vlm_analyzer:
            print("  正在使用 VLM 分析资产数据...")
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
                
                print("  VLM 分析完成")
                
                # 尝试解析和格式化返回结果
                if isinstance(result, dict):
                    # 如果返回的是字典，直接返回
                    return result
                elif isinstance(result, str):
                    # 如果返回的是字符串，尝试解析 JSON
                    try:
                        return json.loads(result)
                    except json.JSONDecodeError:
                        print(f"  警告: VLM 返回的不是有效 JSON: {result}")
                        return {"raw_result": result}
                else:
                    return {"result": result}
                    
            except Exception as e:
                print(f"  VLM 分析失败: {e}")
                import traceback
                traceback.print_exc()
                return None
        else:
            print("  未使用 VLM 分析（VLM 不可用或已禁用）")
            return None
    
    def press_f6_position(self) -> bool:
        """
        按 F6 键 - 持仓
        注意：会先按一次 F1(买入) 进入买入界面，然后按 F6 跳转到持仓
        
        Returns:
            是否成功
        """
        print("执行: F1 -> F6 持仓")
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
        print("执行: F1 -> F7 成交单")
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
        print("执行: F1 -> F8 委托单")
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
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_file = os.path.join(executor.screenshot_dir, f"asset_data_{timestamp}.json")
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(asset_data, f, ensure_ascii=False, indent=2)
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

