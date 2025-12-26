# Quantify
## 机器学习工具包

* 命名实体识别
* 关系抽取
* 实体关系构建
* 情感分析
* 短文本分类

## 股票关系可视化

## 股票历史数据存储

---

## 视觉理解大模型 (VLM)

### 简介

本项目集成了阿里云百炼（DashScope）的视觉理解大模型，支持对截图、图像进行智能分析和理解。

### 获取 API Key

1. **访问阿里云百炼控制台**
   - 打开 [阿里云百炼官网](https://dashscope.aliyun.com/)
   - 登录您的阿里云账号

2. **创建 API Key**
   - 进入控制台后，点击「API-KEY 管理」
   - 点击「创建新的 API Key」
   - 复制生成的 API Key（格式：`sk-xxx`）

3. **注意事项**
   - 新加坡和北京地域的 API Key 不同
   - 获取 API Key 详细步骤：[帮助文档](https://help.aliyun.com/zh/model-studio/get-api-key)

### 配置方式

#### 方式一：环境变量（推荐）

在系统环境变量中设置：

```bash
# Windows PowerShell
$env:DASHSCOPE_API_KEY="sk-xxx"

# Windows CMD
set DASHSCOPE_API_KEY=sk-xxx

# Linux/Mac
export DASHSCOPE_API_KEY="sk-xxx"
```

#### 方式二：配置文件

在 `Config/info.json` 中配置：

```json
{
  "DashScope": {
    "api_key": "sk-xxx",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "qwen3-vl-plus"
  }
}
```

**地域说明：**
- 北京地域：`https://dashscope.aliyuncs.com/compatible-mode/v1`（默认）
- 新加坡地域：`https://dashscope-intl.aliyuncs.com/compatible-mode/v1`

### 支持的模型

本项目默认使用 `qwen3-vl-plus`，您也可以根据需要更换其他模型：

- `qwen3-vl-plus` - 通义千问视觉理解增强版（推荐）
- `qwen-vl-plus` - 通义千问视觉理解标准版
- `qwen-vl-max` - 通义千问视觉理解旗舰版

更多模型列表请参考：[模型列表](https://help.aliyun.com/zh/model-studio/models)

### 使用方法

#### 基本用法

```python
from LLM.VLMImageAnalyzer import VLMImageAnalyzer

# 初始化分析器
analyzer = VLMImageAnalyzer()

# 分析本地图像（文本格式）
result = analyzer.analyze_text(
    image_path="screenshots/screenshot_20251226_145643.png",
    prompt="图中描绘的是什么景象？请详细描述。"
)
print(result)

# 分析网络图像
result = analyzer.analyze_text(
    image_path="https://example.com/image.jpg",
    prompt="请分析这张图片的内容"
)
print(result)
```

#### JSON 格式返回

```python
# 返回 JSON 格式结果
result = analyzer.analyze_json(
    image_path="screenshots/screenshot_20251226_145643.png",
    prompt="请分析这张截图，返回JSON格式，包含：标题、主要内容、关键信息等字段。"
)
print(result)
```

#### 自定义模型

```python
# 使用其他模型
result = analyzer.analyze_text(
    image_path="screenshots/image.png",
    prompt="分析图像内容",
    model="qwen-vl-max"  # 指定模型名称
)
```

### 功能特性

- ✅ 支持本地图像文件（自动 base64 编码）
- ✅ 支持网络图像 URL
- ✅ 支持多种返回格式（文本、JSON、字典）
- ✅ 自动处理图像格式（jpg、png、gif、webp、bmp 等）
- ✅ 灵活的配置方式（环境变量或配置文件）
- ✅ 完善的错误处理

### 使用示例

#### 示例1：分析交易截图

```python
from LLM.VLMImageAnalyzer import VLMImageAnalyzer

analyzer = VLMImageAnalyzer()

# 从交易截图中提取数据
result = analyzer.analyze_json(
    image_path="screenshots/trade_screenshot.png",
    prompt="抽取出其中的交易数据，以json的形式返回。包括代码，名称，价格，数量，是否可行等，如果没有数据则直接置空"
)
print(result)
```

#### 示例2：分析资产截图

```python
# 分析资产数据
result = analyzer.analyze_text(
    image_path="screenshots/asset_screenshot.png",
    prompt="抽取出其中的资产数据，以json的形式返回给我。如果没有数据则直接置空"
)
print(result)
```

### 依赖安装

```bash
pip install openai
```

### 常见问题

1. **ModuleNotFoundError: No module named 'Config'**
   - 确保从项目根目录运行脚本，或使用正确的 Python 路径

2. **API Key 错误**
   - 检查 API Key 是否正确配置
   - 确认 API Key 对应的地域与 base_url 匹配

3. **图像文件不存在**
   - 检查图像路径是否正确
   - 支持相对路径和绝对路径

4. **API 调用失败**
   - 检查网络连接
   - 确认 API Key 是否有效
   - 查看错误信息中的详细提示

### 相关链接

- [阿里云百炼官网](https://dashscope.aliyuncs.com/)
- [API Key 获取指南](https://help.aliyun.com/zh/model-studio/get-api-key)
- [模型列表](https://help.aliyun.com/zh/model-studio/models)
- [API 文档](https://help.aliyun.com/zh/model-studio/developer-reference/api-details-9)

