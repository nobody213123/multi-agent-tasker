# 🤖 CSQAQ 多Agent盯盘系统

基于 Python + LangChain + Playwright + Flask 的 CS:GO/CS2 饰品市场监控系统，支持大盘指数轮询、排行榜展示、饰品价格搜索、走势图分析和 **AI 智能选品推荐**。

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 📊 大盘指数 | 实时展示 23 个品类指数，自动对比涨跌，显示在线人数/市场热度 |
| 🏆 排行榜 | 8 大榜单：价格榜、数量榜、租赁榜、热门榜、平台差价榜、存世量榜、成交榜、挂刀套现 |
| 🤖 AI 选品 | AI 分析多维度数据，生成选品策略、理由、风险提示、目标价位 |
| 🔍 饰品搜索 | 搜索任意饰品，查看 BUFF/悠悠有品/Steam 三平台售价+求购价、涨跌幅、30天走势 |
| 🌐 网页界面 | 浏览器可视化看板，自动刷新，深色主题 |

---

## 项目结构

```
multi-agent-tasker/
├── config.py                  # 全局配置（从 .env 读取）
├── .env                       # 敏感配置（API密钥等，勿提交）
├── .gitignore                 # Git 忽略规则
├── main.py                    # 程序入口（CLI 菜单）
├── README.md                  # 项目说明
├── web/
│   ├── app.py                 # Flask Web 服务器
│   └── templates/
│       └── index.html         # 网页前端（大盘/排行榜/AI选品/搜索）
├── cache/
│   ├── __init__.py
│   ├── data_cache.py          # 本地数据缓存模块
│   ├── data_cache.json        # 饰品数据缓存（自动生成）
│   └── index_cache.json       # 大盘指数缓存（自动生成）
├── tools/
│   ├── __init__.py
│   ├── web_request.py         # 网页请求工具（Playwright）
│   ├── index_api.py           # 大盘指数 API（requests 直调）
│   ├── item_api.py            # 饰品搜索/详情 API（Playwright）
│   ├── chart_renderer.py      # 终端价格走势图渲染（Sparkline）
│   └── recommend.py           # 🤖 AI 选品推荐引擎
└── agents/                    # 多 Agent 模块（扩展用）
    ├── __init__.py
    ├── planner_agent.py       # 总控规划 Agent
    ├── crawler_agent.py       # 数据爬取 Agent
    ├── parser_agent.py        # 数据解析 Agent
    ├── judge_agent.py         # 异动研判 Agent
    └── notice_agent.py        # 消息提醒 Agent
```

---

## 安装步骤

### 1. 安装 Python 依赖

```bash
pip install langchain langchain-community dashscope python-dotenv requests playwright flask
```

### 2. 安装 Playwright 浏览器

```bash
playwright install chromium
```

> 如果下载慢，可设置镜像：
> ```bash
> PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright playwright install chromium
> ```

### 3. 配置 API 密钥

在项目根目录创建 `.env` 文件（已创建好模板）：

```bash
# 编辑 .env，填入你的阿里云百炼 API 密钥
vim .env
```

内容：
```
DASHSCOPE_API_KEY=你的阿里云百炼API密钥
```

或者通过环境变量设置：
```bash
export DASHSCOPE_API_KEY='你的密钥'
```

> API 密钥从 [阿里云百炼控制台](https://bailian.console.aliyun.com/) 获取。

---

## 使用方法

### 启动程序

```bash
cd multi-agent-tasker
python main.py
```

### 主菜单

```
  ╔══════════════════════════════════╗
  ║         主菜单                   ║
  ╠══════════════════════════════════╣
  ║  1. 大盘指数盯盘                 ║
  ║  2. 搜索饰品价格                 ║
  ║  3. 启动网页界面                 ║
  ║  exit → 退出                     ║
  ╚══════════════════════════════════╝
```

---

### 模式 1：大盘指数盯盘（终端）

定时轮询 csqaq.com 全品类指数，对比缓存数据，涨跌标红标绿。

```
╔════════════════════════════════════════════════════════════╗
║ 👥 在线  1,491,883                                       🔥 活跃 ║
║ 🏔 本月峰值  1,492,812  |  月活跃 31,361,348       📈 5137  📉 11153 ║
╠════════════════════════════════════════════════════════════╣
║  饰品指数          1570.33     -36.65   -2.28% ▼           ║
║  租赁指数           570.64      -4.87   -0.85% ▼           ║
║  匕首指数           511.94      +1.10   +0.22% ▲           ║
║  ... 共 23 个品类 ...                                      ║
╚════════════════════════════════════════════════════════════╝
```

- 输入 `exit` 返回主菜单
- 轮询间隔在 `.env` 中设置：`POLL_INTERVAL_SECONDS=300`

---

### 模式 2：搜索饰品价格（终端）

```
请输入饰品名称: 蝴蝶刀

找到 51 个匹配结果:
  1. 蝴蝶刀（★）
  2. 蝴蝶刀（★） | 蓝钢 (战痕累累)
  ...

序号: 1

==================================================
  🗡️  蝴蝶刀（★） 原皮
==================================================
  🔴 BUFF 售价: ¥8,175
  🟡 悠悠有品售价: ¥8,096
  🔵 Steam 售价: ¥12,556
  📈 24h: +0.49%  7天: -2.97%  30天: -12.94%
  📈 近30天走势图 (Sparkline)
```

---

### 模式 3：网页界面（推荐）

```bash
python main.py → 选 3
```

浏览器打开 `http://localhost:8080`

网页界面包含 4 个 Tab：

#### 📊 大盘指数
- 当前在线人数 / 本月峰值 / 月活跃用户
- 市场热度（🔥活跃 / ❄️恐慌）
- 今日涨跌商品统计
- 23 个品类指数表格，涨跌自动标红标绿

#### 🏆 排行榜
8 大榜单，点击饰品可跳转详情：
| 榜单 | 说明 |
|------|------|
| 💰 价格榜 | 24h 涨幅最大的饰品 |
| 📦 数量榜 | 在售数量最多的饰品 |
| 🏠 租赁榜 | 租金最高的饰品 |
| 🔥 热门榜 | 浏览量最高的饰品 |
| 💲 平台差价榜 | BUFF 售价与求购价差最大的饰品 |
| 🏭 存世量榜 | 存世量最少的饰品 |
| 📈 成交榜 | Steam 成交量最大的饰品 |
| 💳 挂刀套现 | Steam 求购挂刀性价比最高的饰品 |

#### 🤖 AI 选品
- 点击「生成推荐」，AI 自动采集大盘 + 多维度榜单数据
- 通义千问分析后生成 3-5 个推荐
- 每个推荐包含：策略（买入/观望/套利）、理由、目标价位、风险提示、信号强度
- 可展开查看原始分析数据

#### 🔍 饰品搜索
- 输入关键词搜索
- 查看 BUFF / 悠悠有品 / Steam 三平台售价+求购价
- 24h / 7天 / 15天 / 30天涨跌幅
- 近30天价格走势图（SVG）
- 在售/求购数量

---

## 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DASHSCOPE_API_KEY` | 阿里云百炼 API 密钥 | 必填 |
| `LLM_MODEL` | 大模型名称 | `qwen-turbo` |
| `MONITOR_URL` | 监控目标网址 | `https://csqaq.com` |
| `POLL_INTERVAL_SECONDS` | 轮询间隔（秒） | `300` |

---

## 依赖

| 包 | 用途 |
|------|------|
| `langchain` | LLM 框架 |
| `langchain-community` | 通义千问 LLM 集成 |
| `dashscope` | 阿里云百炼 SDK |
| `python-dotenv` | 加载 .env 配置 |
| `requests` | HTTP 请求（大盘指数） |
| `playwright` | 无头浏览器（抓取 SPA 页面、排行榜、搜索） |
| `flask` | Web 服务器 |

---

## 硬件要求

| 场景 | 最低配置 | 推荐配置 |
|------|---------|---------|
| 个人使用 | 8GB 内存 + 2核 CPU | 16GB 内存 |
| 3-5 人 | 部署到云服务器 | 2核4G 云服务器 + Docker |
| 更多用户 | 加 Redis 缓存 + 浏览器池 | 4核8G 云服务器 |

> 每次搜索/排行榜请求会启动一个 Chromium 实例（约 300-400MB 内存），并发高时需要更多内存。

---

## 常见问题

**Q: Port 5000 is in use**
> macOS 的 AirPlay 占用 5000 端口，已改为 8080。

**Q: 搜索/排行榜返回空数据**
> 首次加载可能需要几秒（Playwright 启动浏览器），请耐心等待。

**Q: AI 选品返回 API 错误**
> 请确保 `.env` 中的 `DASHSCOPE_API_KEY` 是有效的阿里云百炼密钥。

**Q: playwright install chromium 下载慢**
> 设置镜像源：
> ```bash
> PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright playwright install chromium
> ```

**Q: 内存不够用**
> 关闭 PyCharm、IDE 等大内存应用，或部署到云服务器。

---

## License

MIT
