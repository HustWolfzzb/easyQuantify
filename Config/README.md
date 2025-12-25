# Config 配置模块

配置管理模块，负责统一管理项目的所有配置信息，包括数据库连接、API密钥等敏感信息。

## 📋 功能概述

- **统一配置管理**：集中管理所有系统配置信息
- **跨平台支持**：自动适配Linux、macOS、Windows系统
- **多数据源配置**：支持Tushare、MySQL、MongoDB、Neo4j等配置
- **路径自动解析**：智能查找配置文件路径，支持多种部署方式

## 📁 文件说明

### `Config.py`
配置管理核心模块，提供配置读取和管理功能。

**主要功能：**
- `getFileAbsolutePath()`: 获取配置文件绝对路径，支持跨平台和多种路径查找策略
- `get_BASE_DIR()`: 获取项目基础目录
- `Config` 类: 配置信息读取和管理类

**支持的配置类型：**
- `Tushare` / `tushare` / `ts`: Tushare API配置
- `Mysql` / `mysql` / `MYSQL`: MySQL数据库配置
- `Mongo` / `mongo` / `mongdb`: MongoDB数据库配置
- `Neo4j` / `neo4j`: Neo4j图数据库配置
- `百度` / `baidu`: 百度文字识别配置

### `info.json`
配置文件，存储所有系统配置信息（**注意：包含敏感信息，请勿提交到公开仓库**）

**配置结构：**
```json
{
  "Tushare": {
    "api": "your_tushare_token"
  },
  "Mysql": {
    "user": "username",
    "password": "password",
    "host": "host_address",
    "port": 3306,
    "db": "database_name",
    "charset": "utf8"
  },
  "Mongo": {
    "user": "username",
    "password": "password",
    "host": "host_address",
    "port": 27017,
    "db": "database_name"
  },
  "Neo4j": {
    "name": "username",
    "password": "password",
    "url1": "bolt://localhost:7687",
    "url2": "bolt://remote_host:7687"
  },
  "百度文字识别": {
    "APP_ID": "your_app_id",
    "API_KEY": "your_api_key",
    "SECRECT_KEY": "your_secret_key"
  }
}
```

## 🚀 使用方法

### 基本用法

```python
from Config.Config import Config

# 获取Tushare配置
tushare_config = Config('Tushare')
tushare_info = tushare_config.getInfo()
token = tushare_info['api']

# 获取MySQL配置
mysql_config = Config('Mysql')
mysql_info = mysql_config.getInfo()
# 使用配置连接数据库
# connection = pymysql.connect(**mysql_info)

# 获取MongoDB配置
mongo_config = Config('Mongo')
mongo_info = mongo_config.getInfo()

# 获取Neo4j配置
neo4j_config = Config('Neo4j')
neo4j_info = neo4j_config.getInfo()
```

### 配置类型识别

`Config` 类支持多种配置类型识别方式，以下调用方式等价：

```python
# 以下调用方式都可以识别为Tushare配置
Config('Tushare')
Config('tushare')
Config('TUSHARE')
Config('ts')
```

## ⚙️ 配置说明

### 首次使用

1. **复制配置模板**
   ```bash
   cp info.json.example info.json
   ```

2. **填写配置信息**
   - 在 `info.json` 中填入你的实际配置信息
   - 确保所有必需的配置项都已填写

3. **安全提示**
   - ⚠️ **重要**：`info.json` 包含敏感信息，请勿提交到版本控制系统
   - 建议将 `info.json` 添加到 `.gitignore`
   - 使用环境变量或密钥管理服务管理敏感配置

### 路径查找策略

`getFileAbsolutePath()` 函数按以下顺序查找配置文件：

1. 当前 `Config` 目录下的 `info.json`
2. 系统特定路径（Linux/macOS/Windows）
3. 项目根目录下的 `Config/info.json`
4. 默认路径

## 🔒 安全建议

1. **版本控制**
   - 将 `info.json` 添加到 `.gitignore`
   - 使用 `info.json.example` 作为模板（不包含真实密钥）

2. **环境变量**
   - 考虑使用环境变量存储敏感信息
   - 生产环境建议使用密钥管理服务

3. **权限控制**
   - 限制 `info.json` 文件访问权限
   - 仅授权用户可访问配置文件

## 📝 注意事项

- 配置文件路径查找支持向后兼容，会自动尝试多个路径
- 如果配置文件不存在，会抛出 `FileNotFoundError` 异常
- 配置类型识别不区分大小写，支持多种命名方式
- 建议在项目根目录创建 `info.json.example` 作为配置模板

## 🔗 相关模块

- `DataEngine/Data.py`: 使用Tushare配置
- `DataEngine/Mysql.py`: 使用MySQL配置
- `DataEngine/Mongo.py`: 使用MongoDB配置
- `DataEngine/Neo4j.py`: 使用Neo4j配置

