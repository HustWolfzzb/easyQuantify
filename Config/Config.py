import json
import os
import sys

def getFileAbsolutePath(nowDir=None):
    """
    获取配置文件的绝对路径
    
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
    
    # 如果不存在，尝试其他路径（向后兼容）
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
        # Windows 平台
        path = os.path.join(os.getcwd(), 'Config', 'info.json')
        if os.path.exists(path):
            return path
        # 尝试从当前目录向上查找
        npath = path[:path.find('Quantify') + 9] + path[path.find('Config'):]
        if os.path.exists(npath):
            return npath
    
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
