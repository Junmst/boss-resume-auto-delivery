# BOSS直聘自动投递简历工具 - 详细设计文档

## 项目概述

### 1.1 项目背景
在求职过程中，手动在BOSS直聘上投递简历效率低下，需要重复进行搜索、筛选、沟通等操作。本工具旨在通过自动化技术提升投递效率，解放求职者的时间。

### 1.2 核心目标
- 自动搜索符合条件的职位
- 智能筛选过滤不符合要求的岗位
- 批量投递简历并发送打招呼消息
- 记录投递历史，避免重复投递
- 提供可配置的投递策略

### 1.3 技术栈选型
- **开发语言**: Python 3.8+
- **核心框架**: Selenium WebDriver
- **浏览器驱动**: Chrome/Edge WebDriver
- **数据存储**: SQLite / JSON
- **配置管理**: YAML / JSON
- **日志系统**: logging

---

## 系统架构设计

### 2.1 整体架构


`
┌─────────────────────────────────────────────────────────┐
│                   BOSS自动投递系统                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐      ┌──────────────┐               │
│  │  配置模块    │──────│  日志模块    │               │
│  └──────────────┘      └──────────────┘               │
│          │                     │                       │
│  ┌──────▼─────────────────────▼────────┐              │
│  │         主控制器 (MainController)     │              │
│  └──────┬─────────────────────┬────────┘              │
│         │                     │                       │
│  ┌──────▼──────┐       ┌──────▼──────┐               │
│  │ 浏览器驱动  │       │ 数据管理    │               │
│  │  模块       │       │  模块       │               │
│  └──────┬──────┘       └──────┬──────┘               │
│         │                     │                       │
│  ┌──────▼──────┐       ┌──────▼──────┐               │
│  │ 页面操作    │       │ 历史记录    │               │
│  │  模块       │       │  数据库     │               │
│  └──────┬──────┘       └─────────────┘               │
│         │                                             │
│  ┌──────▼──────────────────────┐                     │
│  │  岗位筛选 & 投递执行模块    │                     │
│  └─────────────────────────────┘                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
`

### 2.2 核心模块说明

#### 2.2.1 配置模块 (ConfigManager)
- 读取用户配置文件
- 管理筛选条件、投递策略
- 支持运行时配置更新

#### 2.2.2 浏览器驱动模块 (BrowserDriver)
- 初始化Selenium WebDriver
- 管理浏览器生命周期
- 处理Cookie登录状态
- 防反爬虫机制

#### 2.2.3 页面操作模块 (PageHandler)
- 封装页面元素定位
- 处理页面交互操作
- 等待页面加载完成
- 处理异常弹窗

#### 2.2.4 岗位筛选模块 (JobFilter)
- 关键词匹配过滤
- 薪资范围判断
- 公司规模筛选
- 黑名单过滤

#### 2.2.5 数据管理模块 (DataManager)
- 投递历史记录
- 去重处理
- 统计分析


### 3.3 自动投递流程

#### 3.3.1 投递策略
- **保守模式**: 严格筛选，投递高质量岗位
- **激进模式**: 放宽筛选，大量投递
- **智能模式**: 根据历史数据动态调整

#### 3.3.2 投递执行代码示例
投递执行器负责完成实际的简历投递操作，包括点击按钮、发送消息、记录历史等。

### 3.4 打招呼消息模板

#### 3.4.1 模板设计
可以设计多个消息模板，程序随机或智能选择：
- 模板1: 您好，我对贵公司的职位很感兴趣，希望能有机会详细沟通。
- 模板2: 您好，看到贵公司在招聘，我的技术栈与岗位要求匹配度很高。
- 模板3: 您好，简历已发送，期待您的回复。

### 3.5 防反爬虫策略

#### 3.5.1 模拟人工行为
- 随机延迟：每次操作间隔3-8秒
- 鼠标移动模拟：移动到元素再点击
- 随机滚动页面：模拟浏览行为
- 隐藏WebDriver特征

#### 3.5.2 请求频率控制
- 每小时投递上限：20个
- 每天投递上限：100个
- 达到限制时自动暂停或停止


---

## 数据库设计

### 4.1 投递历史表 (delivery_history)
```sql
CREATE TABLE delivery_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(100) NOT NULL UNIQUE,
    job_title VARCHAR(200),
    company_name VARCHAR(200),
    company_size VARCHAR(50),
    salary_range VARCHAR(50),
    job_url TEXT,
    hr_name VARCHAR(100),
    delivery_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',
    response_time TIMESTAMP,
    notes TEXT
);
```

### 4.2 公司黑名单表 (company_blacklist)
```sql
CREATE TABLE company_blacklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name VARCHAR(200) NOT NULL UNIQUE,
    reason TEXT,
    added_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.3 投递统计表 (delivery_statistics)
```sql
CREATE TABLE delivery_statistics (
    date DATE PRIMARY KEY,
    total_viewed INTEGER DEFAULT 0,
    total_filtered INTEGER DEFAULT 0,
    total_delivered INTEGER DEFAULT 0,
    response_count INTEGER DEFAULT 0,
    response_rate FLOAT DEFAULT 0
);
```

---

## 配置文件设计

### 5.1 主配置文件 (config.yaml)
```yaml
# 基础配置
app:
  name: "BOSS自动投递工具"
  version: "1.0.0"
  log_level: "INFO"
  
# 浏览器配置
browser:
  type: "chrome"
  headless: false
  user_data_dir: "./browser_data"
  window_size: [1920, 1080]
  
# 搜索配置
search:
  keywords:
    - "Python开发工程师"
    - "后端开发"
  city: "北京"
  experience: "3-5年"
  education: "本科"
  salary_min: 15
  salary_max: 30
  
# 筛选配置
filter:
  required_keywords:
    - "Python"
    - "Django"
  excluded_keywords:
    - "外包"
    - "派遣"
    - "大小周"
  min_salary: 15
  
# 投递配置
delivery:
  mode: "smart"
  max_per_hour: 20
  max_per_day: 100
  greeting_template: "您好，我对贵公司的{position}职位很感兴趣。"
  auto_send_greeting: true
  
# 防反爬配置
anti_crawler:
  min_delay: 3
  max_delay: 8
  random_scroll: true
```

---

## 项目目录结构

```
boss-auto-delivery/
│
├── config/
│   ├── config.yaml          # 主配置文件
│   ├── blacklist.json       # 黑名单配置
│   └── templates.json       # 消息模板
│
├── src/
│   ├── __init__.py
│   ├── main.py              # 主程序入口
│   ├── config_manager.py    # 配置管理
│   ├── browser_driver.py    # 浏览器驱动
│   ├── page_handler.py      # 页面操作
│   ├── job_filter.py        # 岗位筛选
│   ├── delivery_executor.py # 投递执行
│   ├── data_manager.py      # 数据管理
│   ├── session_manager.py   # 会话管理
│   └── utils.py             # 工具函数
│
├── data/
│   ├── cookies.json         # 登录Cookie
│   ├── history.db           # SQLite数据库
│   └── logs/                # 日志文件
│
├── drivers/
│   ├── chromedriver.exe     # Chrome驱动
│   └── msedgedriver.exe     # Edge驱动
│
├── requirements.txt         # 依赖包
├── README.md                # 使用说明
└── run.py                   # 启动脚本
```

---

## 依赖包清单

### requirements.txt
```
selenium>=4.10.0
pyyaml>=6.0
requests>=2.31.0
```

---

## 使用说明

### 8.1 安装步骤

1. **安装Python环境**
   - 确保已安装 Python 3.8 或更高版本

2. **安装依赖包**
   ```bash
   pip install -r requirements.txt
   ```

3. **下载浏览器驱动**
   - 下载对应版本的 ChromeDriver
   - 放置到 drivers/ 目录下

4. **配置文件**
   - 修改 config/config.yaml 中的搜索条件
   - 根据需求调整筛选规则和投递策略

### 8.2 运行程序

```bash
python run.py
```

### 8.3 首次使用

1. 程序启动后会打开浏览器
2. 手动扫码登录BOSS直聘
3. 登录完成后按回车继续
4. 程序将自动开始搜索和投递

### 8.4 注意事项

⚠️ **重要提示**：

1. **合规使用**: 本工具仅供学习交流使用，请遵守BOSS直聘平台规则
2. **频率控制**: 建议设置合理的投递频率，避免被平台检测
3. **筛选策略**: 建议设置严格的筛选条件，提高投递质量
4. **定期维护**: BOSS直聘页面结构可能变化，需要及时更新选择器
5. **账号安全**: 妥善保管Cookie文件，避免泄露

---

## 优化建议

### 9.1 功能扩展

1. **AI增强**
   - 集成GPT生成个性化打招呼消息
   - 智能分析职位描述匹配度
   - 自动生成投递报告

2. **数据分析**
   - 投递效果统计分析
   - 回复率趋势图表
   - 热门岗位推荐

3. **多平台支持**
   - 扩展到拉勾、猎聘等平台
   - 统一管理多平台投递

4. **通知功能**
   - 邮件通知投递结果
   - 微信/钉钉消息推送
   - HR回复提醒

### 9.2 性能优化

1. **并发处理**: 使用多线程/异步提升效率
2. **缓存机制**: 缓存页面数据减少请求
3. **增量更新**: 只处理新增职位
4. **断点续传**: 支持中断后继续运行

---

## 法律声明

本工具仅供技术学习和研究使用，使用者需遵守：

1. **平台协议**: 遵守BOSS直聘用户协议和使用条款
2. **合理使用**: 不得进行恶意刷量、垃圾信息发送
3. **个人责任**: 使用本工具产生的一切后果由使用者自行承担
4. **开源协议**: 本项目采用MIT开源协议

---

## 常见问题 FAQ

### Q1: 为什么登录失败？
A: 检查Cookie是否过期，尝试删除cookies.json重新登录

### Q2: 为什么没有投递成功？
A: 检查页面元素选择器是否正确，BOSS直聘可能更新了页面结构

### Q3: 如何避免被封号？
A: 
- 设置合理的投递频率（建议每天不超过50个）
- 增加随机延迟时间
- 使用真实浏览器模式（非headless）

### Q4: 如何自定义筛选条件？
A: 修改 config/config.yaml 文件中的 filter 配置

### Q5: 支持哪些浏览器？
A: 目前支持 Chrome 和 Edge，推荐使用 Chrome

---

## 更新日志

### v1.0.0 (2026-07-13)
- ✅ 基础框架搭建
- ✅ 登录会话管理
- ✅ 职位搜索和筛选
- ✅ 自动投递简历
- ✅ 防反爬虫策略
- ✅ 投递历史记录

### 未来计划
- 🔲 支持多平台投递
- 🔲 AI智能消息生成
- 🔲 Web可视化界面
- 🔲 移动端APP

---

**祝您求职顺利！** 🎉



