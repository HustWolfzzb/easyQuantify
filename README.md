# EasyQuantify

<div align="center">

**一个基于Python的A股量化交易系统**

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

*数据驱动 · 策略制胜 · 理性交易*

</div>

---

## 📖 项目简介

EasyQuantify 是一个面向A股市场的量化交易系统，集成了数据获取、特征提取、策略回测、情绪分析和自动化交易等功能。系统旨在通过数据分析和算法策略，帮助投资者进行理性决策，减少情绪化交易的影响。

### ✨ 核心特性

- 📊 **多源数据集成**：支持Tushare、easyquotation等多种数据源
- 🧠 **知识图谱**：基于Neo4j构建股票知识图谱，支持概念、行业、地区等多维度分析
- 📈 **特征工程**：内置多种技术指标（MA、RSI、动量等）和特征提取工具
- 🤖 **多策略支持**：网格交易、神经网络、决策树、动量策略等多种交易策略
- 📰 **情绪分析**：基于新闻文本的金融情绪分析，支持LSTM深度学习模型
- 🔄 **自动化交易**：集成easytrader，支持实盘自动化交易
- 📉 **行情监控**：实时监控ETF、指数和个股行情

---

## 🚀 回归宣言

**我回来了，大A！**

时隔多年，我重新回到这个曾经让我又爱又恨的市场。这一次，我不再是那个凭感觉交易的韭菜，也不再是那个对代码不自信的新手。

经过这些年的沉淀和成长，我带着更成熟的技术栈、更完善的量化框架，以及更理性的交易心态，重新站在了起跑线上。

**这一次，我要用数据说话，用策略制胜，用代码守护我的钱包。**

让量化成为我的武器，让理性战胜情绪，让代码替我执行纪律。

大A，我准备好了。这一次，我们好好较量一番！

---

## 🛠️ 技术栈

### 数据层
- **Tushare**：股票、ETF、基金、指数等历史数据和实时新闻
- **MongoDB**：历史分时数据存储
- **MySQL**：结构化数据存储
- **Neo4j**：知识图谱存储

### 交易层
- **TongHuaShunExecutor**：同花顺下单程序执行器，基于Windows窗口操作和图像识别实现自动化交易
- **easytrader**：自动化交易接口（传统方式）
- **easyquotation**：实时行情获取

### 算法层
- **NumPy/Pandas**：数据处理和分析
- **Scikit-learn**：机器学习模型（决策树等）
- **TensorFlow/Keras**：深度学习模型（LSTM情绪分析）

### 可视化
- **Matplotlib/Plotly**：数据可视化

---

## 📁 项目结构

```
easyQuantify/
├── Config/                 # 配置文件
│   ├── Config.py          # 配置管理
│   └── info.json          # 配置信息
├── DataEngine/            # 数据引擎
│   ├── Data.py            # Tushare数据获取
│   ├── Mongo.py           # MongoDB操作
│   ├── Mysql.py           # MySQL操作
│   ├── Neo4j.py           # Neo4j知识图谱
│   ├── fund_protfolio.py  # 基金持仓数据
│   └── etf.py             # ETF数据
├── Feature/               # 特征提取
│   ├── pre_process_data.py # 数据预处理
│   ├── feature.py         # 特征计算
│   ├── shape.py           # 形态识别
│   └── trend.py           # 趋势分析
├── Strategy/              # 交易策略
│   ├── gridTrade.py       # 网格交易策略
│   ├── Neural_Network.py  # 神经网络策略
│   ├── DecisionTree.py    # 决策树选股
│   ├── ThreeMomentum.py   # 三重动量策略
│   ├── MovingAverage.py   # 均线策略
│   └── follow_fund.py     # 跟庄策略
├── Monitor/               # 行情监控
│   ├── Market.py          # 市场监控
│   └── ScreenSpyer.py     # 屏幕监控
├── Sentiment analysis/    # 情绪分析
│   ├── simple.py          # 简单情绪分析
│   └── News/              # 新闻获取
├── Trade/                 # 交易执行
│   ├── TongHuaShunExecutor.py  # 同花顺自动化交易执行器
│   ├── Operation.py       # 交易操作（easytrader接口）
│   └── Entity.py          # 交易实体
├── RiskControl/           # 风险控制
│   └── RiskControl.py     # 风控模块
├── ML/                    # 机器学习
├── UI/                    # 用户界面
├── cache/                 # 缓存文件
│   ├── code-log.txt       # 操作日志
│   ├── gaps.txt           # 价差配置
│   ├── buy_rates.txt      # 买入价差率
│   └── sell_rates.txt     # 卖出价差率
├── graph_data/            # 图谱数据
├── main.py                # 主程序入口
└── README.md              # 项目说明
```

---

## 🔧 安装与配置

### 环境要求

- Python 3.7+
- MongoDB（可选，用于历史分时数据）
- MySQL（可选，用于结构化数据）
- Neo4j（可选，用于知识图谱）

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/yourusername/easyQuantify.git
cd easyQuantify
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置信息**
   - 在 `Config/info.json` 中配置数据库连接信息
   - 配置Tushare Token
   - 配置交易接口（easytrader）

### 配置文件说明

`Config/info.json` 需要包含以下配置：

```json
{
  "Tushare": {
    "token": "your_tushare_token"
  },
  "Mysql": {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "password",
    "database": "quantify"
  },
  "Mongo": {
    "host": "localhost",
    "port": 27017,
    "database": "quantify"
  },
  "Neo4j": {
    "uri": "bolt://localhost:7687",
    "user": "neo4j",
    "password": "password"
  }
}
```

---

## 📚 模块说明

### 1. 数据引擎 (DataEngine)

#### Tushare 数据获取
- **功能**：获取股票、ETF、基金、指数等历史数据，以及实时新闻
- **文件**：`DataEngine/Data.py`
- **支持数据类型**：
  - 股票基础信息
  - 历史K线数据
  - 财务数据
  - 新闻资讯

#### 历史分时数据
- **功能**：爬取和存储股票历史分时数据
- **文件**：`DataEngine/Mongo.py`
- **存储**：MongoDB

#### 知识图谱
- **功能**：基于Neo4j构建股票知识图谱
- **文件**：`DataEngine/Neo4j.py`
- **图谱维度**：
  - 概念关联
  - 行业分类
  - 地区分布
- **数据来源**：Tushare分类数据

#### 基金持仓数据
- **功能**：获取基金持仓信息
- **文件**：`DataEngine/fund_protfolio.py`
- **说明**：由于Tushare对基金持仓数据有积分要求，本模块未来将提供替代方案

---

### 2. 特征提取 (Feature)

#### 数据预处理
- **功能**：对原始数据进行清洗和预处理
- **文件**：`Feature/pre_process_data.py`
- **技术指标**：
  - `delta_ma5_vol`：5日均量变化率
  - `delta_ma5`：5日均线变化率
  - 五日动量
  - 二十日动量
  - RSI相对强弱指标

#### 特征计算
- **功能**：基于技术指标计算交易特征
- **文件**：`Feature/feature.py`
- **支持**：自定义特征工程流程

---

### 3. 行情监控 (Monitor)

#### A股市场监控
- **功能**：监控A股市场行情并输出可视化图表
- **文件**：`Monitor/Market.py`
- **监控对象**：
  - 全部ETF
  - 主要指数
  - 全部股票
- **状态**：非实时监控，后续将完善实时功能

---

### 4. 情绪分析 (Sentiment Analysis)

#### 新闻监控与情绪分析
- **功能**：实时获取财经新闻并进行情绪分析
- **文件**：`Sentiment analysis/simple.py`
- **分析方法**：
  - 基于金融情绪词典的统计学分析
  - 支持实时新闻抓取

#### 机器学习情绪分析
- **功能**：基于LSTM的深度学习情绪分析
- **模型**：LSTM神经网络
- **说明**：需要配合完善的产业链知识图谱和金融实体识别使用

---

### 5. 交易策略 (Strategy)

#### 网格交易策略 ⭐
- **功能**：优化的网格交易策略，支持动态配置买卖价差
- **文件**：`Strategy/gridTrade.py`
- **特点**：
  - 动态配置价格差
  - 支持浮动价差率
  - 持仓管理：不盈利不放手
- **配置说明**：
  - `cache/code-log.txt`：记录最后一次操作的价格和数量
  - `cache/gaps.txt`：各股票的价差配置
  - `cache/buy_rates.txt`：买入浮动价差率
  - `cache/sell_rates.txt`：卖出浮动价差率

#### 决策树选股
- **功能**：基于决策树模型预测次日涨跌
- **文件**：`Strategy/DecisionTree.py`
- **模型类型**：分类模型

#### 神经网络策略
- **功能**：基于神经网络的预测模型
- **文件**：`Strategy/Neural_Network.py`
- **特点**：简化版神经网络模型

#### 动量与均线策略
- **功能**：三重动量策略和均线策略
- **文件**：`Strategy/ThreeMomentum.py`, `Strategy/MovingAverage.py`
- **说明**：适用于特定个股和特定时期

---

### 6. 交易执行 (Trade)

#### 同花顺自动化交易执行器 ⭐
- **功能**：基于Windows窗口操作和图像识别实现同花顺下单程序的自动化交易
- **文件**：`Trade/TongHuaShunExecutor.py`
- **核心特性**：
  - **自动化下单**：支持买入（F1）、卖出（F2）、撤单（F3）等操作
  - **订单模式**：支持限价单和市价单模式
    - 限价单：使用指定价格下单
    - 市价单：自动计算价格（买入比基准价高1%，卖出比基准价低1%），保持小数位数一致
  - **资产查询**：通过F4键查询资产，支持VLM图像分析自动提取资产数据
  - **持仓管理**：支持查询持仓（F6）、成交单（F7）、委托单（F8）
  - **交易时间检查**：自动检查交易时间（9:25-15:00），非交易时间拒绝执行
  - **日志系统**：完整的日志记录和文件管理
    - 自动保存截图到 `SystemLog/screenshots/`
    - 自动保存资产数据到 `SystemLog/assets/`
    - 日志文件保存到 `SystemLog/logs/`
    - 自动清理超过7天的过期文件
  - **窗口管理**：自动查找、聚焦和操作同花顺交易窗口
  - **VLM集成**：可选集成视觉语言模型进行图像分析
- **依赖**：
  - **pywin32**：Windows API操作
  - **PIL/Pillow**：图像处理
  - **VLMImageAnalyzer**（可选）：视觉语言模型分析

#### 传统自动化交易接口
- **功能**：集成easytrader和easyquotation实现自动化交易
- **文件**：`Trade/Operation.py`, `Trade/Entity.py`
- **依赖**：
  - **easytrader**：自动化交易接口，需按官网配置
  - **easyquotation**：实时股价获取，比Tushare快10倍
  - **Tushare**：底层数据支持

---

## 💡 使用示例

### 网格交易配置示例

1. **配置价差** (`cache/gaps.txt`)
```
000001:0.02
000002:0.015
510300:0.01
```

2. **配置买入价差率** (`cache/buy_rates.txt`)
```
000001:0.95
000002:0.98
```

3. **配置卖出价差率** (`cache/sell_rates.txt`)
```
000001:1.05
000002:1.02
```

### 同花顺自动化交易示例

```python
from Trade.TongHuaShunExecutor import TongHuaShunExecutor

# 初始化执行器
exe_path = r"D:\Program Files (x86)\ths\同花顺\xiadan.exe"
executor = TongHuaShunExecutor(exe_path)

# 启动或激活程序
if executor.launch_program() or executor.activate_window():
    # 限价买入
    executor.press_f1_buy(
        stock_code_or_name="000001",
        price="10.50",
        quantity="100",
        price_mode="limit"
    )
    
    # 市价买入（比基准价高1%）
    executor.press_f1_buy(
        stock_code_or_name="000001",
        price="10.50",  # 基准价格
        quantity="100",
        price_mode="market"  # 自动计算为 10.605
    )
    
    # 查询资产（使用VLM分析）
    asset_data = executor.press_f4_query(use_vlm=True)
    print(asset_data)
```

## ⚠️ 风险提示

1. **投资有风险，入市需谨慎**
   - 本系统仅供学习和研究使用
   - 实盘交易存在资金损失风险
   - 历史收益不代表未来表现

2. **技术风险**
   - 系统可能存在bug，请充分测试后再使用
   - 网络延迟可能导致交易执行偏差
   - 数据源异常可能影响策略效果

3. **合规风险**
   - 请确保交易行为符合相关法律法规
   - 注意API调用频率限制
   - 遵守交易所交易规则

---

## 📝 项目历史

### 初心

疫情期间，在家学习时学校发了补助，恰逢股市动荡，后续开启了波澜壮阔的大牛市，于是入场开始炒股。

苦于无人交流，以及未曾接受系统化的经济学教育，在几次大亏之后，决定结合所学知识进行量化交易，希望通过代码帮助自己进行理性决策。

项目从2020年开始，2021年逐步完善。在2021-05-12至2021-06-01期间，进行了网格交易策略的实盘测试，总投入从一万加到三万四，收益847元（2.5%），得益于五月份的好行情。测试期间主要选择权重股、ETF和少量波动较大的股票。

现在，重新审视这个项目，带着新的认知和技术，准备让它发挥更大的作用。

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

---

## 📄 许可证

本项目采用 MIT 许可证。

---

## 📮 联系方式

如有问题或建议，欢迎通过Issue反馈。

---

<div align="center">

**让量化成为武器，让理性战胜情绪，让代码执行纪律**

Made with ❤️ for A股量化交易

</div>
