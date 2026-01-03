import json
import os
import sys
import inspect

def getFileAbsolutePath(nowDir=None):
    """
    获取配置文件的绝对路径
    
    查找策略：
    1. 首先尝试当前文件（Config.py）所在目录下的 info.json
    2. 如果找不到，获取调用该函数的文件的绝对路径
    3. 根据调用文件的位置，尝试相对路径查找 Config/info.json
    
    Args:
        nowDir: 未使用，保持向后兼容
        
    Returns:
        str: info.json 的绝对路径
    """
    # 获取当前文件所在目录（Config目录）
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(current_file_dir, 'info.json')
    
    # 如果文件存在，直接返回
    if os.path.exists(config_file):
        return config_file
    
    # 如果不存在，尝试根据调用文件的绝对路径查找
    try:
        # 获取调用栈，找到调用 getFileAbsolutePath 的文件
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        if caller_frame:
            caller_file = caller_frame.f_code.co_filename
            caller_abs_path = os.path.abspath(caller_file)
            caller_dir = os.path.dirname(caller_abs_path)
            
            # 策略1: 尝试调用文件所在目录的 Config/info.json
            relative_config = os.path.join(caller_dir, 'Config', 'info.json')
            if os.path.exists(relative_config):
                return relative_config
            
            # 策略2: 尝试调用文件上级目录的 Config/info.json
            parent_dir = os.path.dirname(caller_dir)
            relative_config = os.path.join(parent_dir, 'Config', 'info.json')
            if os.path.exists(relative_config):
                return relative_config
            
            # 策略3: 从调用文件所在目录向上查找，直到找到包含 Config/info.json 的目录
            search_dir = caller_dir
            max_levels = 10  # 最多向上查找10层
            for level in range(max_levels):
                test_path = os.path.join(search_dir, 'Config', 'info.json')
                if os.path.exists(test_path):
                    return test_path
                # 向上移动一层
                parent = os.path.dirname(search_dir)
                if parent == search_dir:  # 已经到达根目录
                    break
                search_dir = parent
    except Exception:
        # 如果获取调用栈失败，继续使用其他方法
        pass
    
    # 如果都找不到，尝试其他路径（向后兼容）
    if sys.platform == 'linux':
        # 尝试硬编码路径
        hardcoded_path = "/home/zzb/Quantify/easyQuantify/Config/info.json"
        if os.path.exists(hardcoded_path):
            return hardcoded_path
        # 尝试旧路径
        old_path = "/home/zzb/Quantify/Config/info.json"
        if os.path.exists(old_path):
            return old_path
    elif sys.platform == 'darwin':
        hardcoded_path = "/Users/zhangzhaobo/PycharmProjects/Quantify/easyQuantify/Config/info.json"
        if os.path.exists(hardcoded_path):
            return hardcoded_path
        old_path = "/Users/zhangzhaobo/PycharmProjects/Quantify/Config/info.json"
        if os.path.exists(old_path):
            return old_path
    else:
        # Windows 平台：尝试当前工作目录
        path = os.path.join(os.getcwd(), 'Config', 'info.json')
        if os.path.exists(path):
            return path
        # 尝试从当前目录向上查找
        search_dir = os.getcwd()
        max_levels = 10
        for level in range(max_levels):
            test_path = os.path.join(search_dir, 'Config', 'info.json')
            if os.path.exists(test_path):
                return test_path
            parent = os.path.dirname(search_dir)
            if parent == search_dir:
                break
            search_dir = parent
    
    # 如果都找不到，返回默认路径
    return config_file

def get_BASE_DIR():
    d = os.getcwd()
    if d.find('\\') != -1:
        return d[:d.rfind('\\')]
    else:
        return d[:d.rfind('/')]

class Config():
    def __init__(self, type):
        info = getFileAbsolutePath()
        self.data = {}
        self.type = type
        if not os.path.exists(info):
            raise FileNotFoundError(f"配置文件不存在: {info}")
        with open(info, 'r', encoding='utf8') as f:
            self.data = json.load(f)

    def getInfo(self):
        if self.type.find('百度')!=-1 or self.type.find('baidu')!=-1:
            return self.data['百度文字识别']
        if self.type.find('mysql')!=-1 or self.type.find('Mysql')!=-1 or self.type.find('MYSQL')!=-1:
            return self.data['Mysql']
        if self.type.lower().find('mongo')!=-1 or self.type.lower().find('mongdb')!=-1 :
            return self.data['Mongo']
        if self.type.find('Tushare')!=-1 or self.type.find('TUSHARE')!=-1 or self.type.find('tushare')!=-1 or self.type.find('ts')!=-1:
            return self.data['Tushare']
        if self.type.find('Neo4j') != -1 or self.type.find('neo4j') != -1:
            return self.data['Neo4j']
        if self.type.find('DashScope')!=-1 or self.type.find('dashscope')!=-1 or self.type.find('dash')!=-1 or self.type.find('vl')!=-1 or self.type.find('VLM')!=-1:
            return self.data['DashScope']
