"""
VLM 截图理解模块
用于根据 prompt 和图像地址，返回指定格式的内容
支持本地文件路径和网络URL
"""
import os
import sys
import base64
import json
from typing import Optional, Dict, Any, Union
from openai import OpenAI

# 添加项目根目录到 Python 路径，以便导入 Config 模块
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_current_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from Config.Config import Config


class VLMImageAnalyzer:
    """
    视觉语言模型图像分析器
    使用阿里云 DashScope API (Qwen3-VL-Plus) 进行图像理解
    """
    
    def __init__(self, config_type: str = "DashScope"):
        """
        初始化 VLM 图像分析器
        
        Args:
            config_type: 配置类型，默认为 "DashScope"
        """
        self.config = Config(config_type)
        self.config_data = self.config.getInfo()
        
        # 优先使用环境变量，如果没有则使用配置文件
        api_key = os.getenv("DASHSCOPE_API_KEY") or self.config_data.get("api_key", "")
        if not api_key:
            raise ValueError("未找到 DashScope API Key，请设置环境变量 DASHSCOPE_API_KEY 或在配置文件中配置")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.config_data.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        )
        self.model = self.config_data.get("model", "qwen3-vl-plus")
    
    def _encode_image(self, image_path: str) -> str:
        """
        将本地图像文件编码为 base64
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            str: base64 编码的图像数据
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图像文件不存在: {image_path}")
        
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _is_url(self, path: str) -> bool:
        """
        判断是否为 URL
        
        Args:
            path: 路径或URL
            
        Returns:
            bool: 是否为URL
        """
        return path.startswith("http://") or path.startswith("https://")
    
    def _prepare_image_url(self, image_path: str) -> str:
        """
        准备图像URL，支持本地文件和网络URL
        
        Args:
            image_path: 图像路径或URL
            
        Returns:
            str: 图像URL（base64 data URI 或原始URL）
        """
        if self._is_url(image_path):
            # 如果是网络URL，直接返回
            return image_path
        else:
            # 如果是本地文件，编码为 base64
            base64_image = self._encode_image(image_path)
            # 根据文件扩展名确定 MIME 类型
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.bmp': 'image/bmp'
            }.get(ext, 'image/jpeg')
            
            return f"data:{mime_type};base64,{base64_image}"
    
    def analyze(
        self, 
        image_path: str, 
        prompt: str,
        response_format: Optional[str] = None,
        model: Optional[str] = None
    ) -> Union[str, Dict[str, Any]]:
        """
        分析图像并返回结果
        
        Args:
            image_path: 图像路径（本地文件路径或网络URL）
            prompt: 提示词，描述需要从图像中提取的信息
            response_format: 返回格式，可选值：
                - None 或 "text": 返回纯文本
                - "json": 返回 JSON 格式（如果模型支持）
                - "dict": 返回字典格式
            model: 模型名称，默认使用配置文件中的模型
            
        Returns:
            str 或 Dict: 分析结果，根据 response_format 返回不同格式
        """
        # 准备图像URL
        image_url = self._prepare_image_url(image_path)
        
        # 使用指定的模型或默认模型
        model_name = model or self.model
        
        # 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt
                    },
                ],
            },
        ]
        
        # 准备请求参数
        request_params = {
            "model": model_name,
            "messages": messages,
        }
        
        # 如果指定了 JSON 格式，添加相应参数
        if response_format == "json":
            request_params["response_format"] = {"type": "json_object"}
        
        try:
            # 调用 API
            completion = self.client.chat.completions.create(**request_params)
            
            # 获取响应内容
            content = completion.choices[0].message.content
            
            # 根据格式返回
            if response_format == "json" or response_format == "dict":
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    # 如果解析失败，返回原始文本
                    return {"content": content, "raw": True}
            else:
                return content
                
        except Exception as e:
            raise RuntimeError(f"VLM API 调用失败: {str(e)}")
    
    def analyze_json(
        self, 
        image_path: str, 
        prompt: str,
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析图像并返回 JSON 格式结果（便捷方法）
        
        Args:
            image_path: 图像路径
            prompt: 提示词
            model: 模型名称，可选
            
        Returns:
            Dict: JSON 格式的分析结果
        """
        return self.analyze(image_path, prompt, response_format="json", model=model)
    
    def analyze_text(
        self, 
        image_path: str, 
        prompt: str,
        model: Optional[str] = None
    ) -> str:
        """
        分析图像并返回文本格式结果（便捷方法）
        
        Args:
            image_path: 图像路径
            prompt: 提示词
            model: 模型名称，可选
            
        Returns:
            str: 文本格式的分析结果
        """
        return self.analyze(image_path, prompt, response_format="text", model=model)


if __name__ == "__main__":
    # 示例用法
    analyzer = VLMImageAnalyzer()
    
    # 示例1: 分析本地图像文件
    # result = analyzer.analyze_text(
    #     image_path="screenshots/screenshot_20251226_144747.png",
    #     prompt="抽取出其中的数据，以json的形式返回给我。包括代码，名称，价格，数量，是否可行等，如果没有数据则直接置空"
    # )
    # print(result)
    result = analyzer.analyze_text(
        image_path="screenshots/image.png",
        prompt="抽取出其中的资产数据，以json的形式返回给我。如果没有数据则直接置空"
    )
    print(result)
    
    # 示例2: 分析网络图像
    # result = analyzer.analyze_text(
    #     image_path="https://help-static-aliyun-doc.aliyuncs.com/file-manage-files/zh-CN/20241022/emyrja/dog_and_girl.jpeg",
    #     prompt="图中描绘的是什么景象？"
    # )
    # print(result)
    
    # 示例3: 返回 JSON 格式
    # result = analyzer.analyze_json(
    #     image_path="screenshots/screenshot_20251226_145643.png",
    #     prompt="请分析这张截图，返回JSON格式，包含：标题、主要内容、关键信息等字段。"
    # )
    # print(json.dumps(result, ensure_ascii=False, indent=2))
    
    pass

