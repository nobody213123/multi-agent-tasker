# CSQAQ 多Agent盯盘系统

基于 Python + LangChain + Playwright + Flask 的 CS:GO/CS2 饰品市场监控系统，6层架构，双 Agent 实时交互，接入通义千问大模型进行 AI 选品推荐。

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        入口层 (entry/)                               │
│            CLI (cli.py)  /  Web Server (web.py)                      │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│                       编排层 (orchestration/)                        │
│  ┌─────────────────┐    ┌──────────────────┐    ┌───────────────┐  │
│  │   Coordinator   │───▶│  CollectorAgent  │◀──▶│ AnalyzerAgent │  │
│  │  (线程安全调度)   │    │  (Playwright采集) │    │ (LLM两阶段分析) │  │
│  └─────────────────┘    └──────────────────┘    └───────────────┘  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│                       模型层 (models/)                               │
│  AnalysisResult / Recommendation / CollectedData / RankItem / Item  │
│  MarketOverview / TrendSignal / BacktestReport / CycleResult        │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│                       工具层 (tools/)                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ LLM Provider │  │  Providers   │  │ index_api / item_api     │  │
│  │ Qwen/Mock    │  │ Csqaq / Mock │  │ chart_renderer / ...     │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│                       记忆层 (memory/)                               │
│  RecommendationStore / PriceStore / BacktestEngine / CacheStore     │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│                       观测层 (observability/)                        │
│                        Logger / Metrics                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent 通信

```
CollectorAgent ──collect_all()──▶ CollectedData ──▶ AnalyzerAgent
      ▲                                                    │
      │              fetch_details(names)                  │
      ◀────────────────────────────────────────────────────┘
                     (双向实时交互)
```

- **CollectorAgent**: 采集大盘指数 + 多维度榜单（Playwright）
- **AnalyzerAgent**: 两阶段 LLM 分析：
  1. 第一阶段：分析市场数据，输出 `DATA_NEEDS: 饰品A, 饰品B`
  2. 按需从 CollectorAgent 获取详情数据
  3. 第二阶段：结合补充数据，生成最终 JSON 推荐

### T+7 结算机制

系统自动考虑 Buff 平台的 **T+7 结算规则**（卖出后资金锁定 7 天到账）：
- 短线策略（< 7 天快进快出）被标记为高风险，因资金无法快速周转
- "买入"推荐仅当预期持有期 > 7 天且趋势看涨时给出
- 套利策略会评估 7 天锁仓期的价格反向波动风险
- LLM prompt 中内置 T+7 约束，每次推荐都自动考量

## 功能概览

| 功能 | 说明 |
|------|------|
| 📊 大盘指数 | 实时展示 23 个品类指数，自动对比涨跌，显示在线人数/市场热度 |
| 🏆 排行榜 | 多维度榜单：价格榜、热门榜、存世量榜、成交榜、平台差价榜等 |
| 🤖 AI 选品 | LLM 两阶段分析：先分析 Trend Signal，再按需获取详情，生成带 T+7 风险评估的推荐 |
| 🔍 饰品搜索 | 搜索任意饰品，查看 BUFF/悠悠有品/Steam 三平台售价+求购价、涨跌幅、30天走势 |
| 🌐 网页界面 | 浏览器可视化看板，深色主题，自动缓存 |

## 项目结构

```
multi-agent-tasker/
├── config.py                  # 全局配置（从 os.environ 读取）
├── env.py                     # .env 静默加载器
├── main.py                    # CLI 入口（→ entry.cli）
├── logger.py                  # 结构化日志（→ observability.logger）
├── pyproject.toml             # 项目元数据 + lint 配置
├── requirements.txt           # 依赖锁文件
├── Makefile                   # test/lint/clean
├── Dockerfile                 # 容器化部署
├── .github/workflows/         # CI/CD
│
├── entry/                     # 入口层
│   ├── __init__.py
│   ├── cli.py                 # CLI 主菜单（大盘盯盘/搜索/Web）
│   └── web.py                 # Flask Web 服务器（8个 API 端点）
│
├── orchestration/             # 编排层
│   ├── __init__.py
│   ├── coordinator.py         # 线程安全调度器
│   └── agents/
│       ├── __init__.py
│       ├── collector.py       # CollectorAgent
│       └── analyzer.py        # AnalyzerAgent（两阶段 LLM）
│
├── models/                    # 模型层（纯 dataclass，零依赖）
│   ├── __init__.py
│   ├── analysis.py            # CycleResult, Recommendation, RankItem, etc.
│   ├── market.py              # MarketIndex, MarketOverview, etc.
│   ├── item.py                # Item, ChartData, SearchResult
│   └── message.py             # DataRequest, ExtraData
│
├── tools/                     # 工具层
│   ├── __init__.py
│   ├── llm.py                 # LLMProvider / QwenLLMProvider / MockLLMProvider
│   ├── index_api.py           # 指数采集（requests）
│   ├── item_api.py            # 饰品搜索/详情（Playwright）
│   ├── chart_renderer.py      # 走势图渲染
│   ├── web_request.py         # 通用 HTTP 请求
│   └── providers/             # Provider 接口 + 实现
│       ├── __init__.py
│       ├── interfaces.py      # IndexProvider / RankProvider / SearchProvider
│       ├── csqaq.py           # CsqaqIndex / CsqaqRank / CsqaqSearch
│       └── mock.py            # MockIndex / MockRank / MockSearch
│
├── memory/                    # 记忆层
│   ├── __init__.py
│   ├── recommendation_store.py # 推荐记录持久化
│   ├── price_store.py         # 价格快照
│   ├── backtest_engine.py     # 回测引擎（命中率计算）
│   └── cache_store.py         # 缓存层
│
├── observability/             # 观测层
│   ├── __init__.py
│   └── logger.py              # 结构化日志（替代 print）
│
├── providers/                 # （旧接口, 保留兼容）→ tools.providers
├── storage/                   # （旧存储, 保留兼容）→ memory
├── agents/                    # （旧 Agent, 保留兼容）→ orchestration.agents
│
├── web/
│   ├── app.py                 # （旧入口, 保留兼容）→ entry.web
│   └── templates/
│       └── index.html         # 前端（深色主题, Tailwind CSS）
│
└── tests/                     # 测试（27 个用例，全部通过）
    ├── conftest.py
    ├── test_agents.py
    ├── test_models.py
    ├── test_orchestrator.py
    └── test_providers.py
```

## 安装步骤

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 Playwright 浏览器

```bash
playwright install chromium
```

如果下载慢，可设置镜像：
```bash
PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright playwright install chromium
```

### 3. 配置 API 密钥

```bash
cp .env.example .env
```

编辑 `.env`：

```ini
DASHSCOPE_API_KEY=你的阿里云百炼API密钥
LLM_MODEL=qwen-max
MONITOR_URL=https://csqaq.com
POLL_INTERVAL_SECONDS=300
```

## 使用方法

### Web 界面（推荐）

```bash
python entry/web.py
```

浏览器打开 `http://localhost:8080`

### CLI 模式

```bash
python main.py
```

主菜单 → 选 `1` 大盘盯盘 / `2` 搜索 / `3` 启动网页界面

### 运行测试

```bash
pytest tests/ -q
# 全部 27 个用例通过
```

## API 端点

| 端点 | 说明 | 缓存 |
|------|------|------|
| `GET /` | 网页主界面 | — |
| `GET /api/indices` | 大盘指数数据 | — |
| `GET /api/rank?type=price` | 排行榜（price/hot/supply/turnover/diff） | 5分钟 |
| `GET /api/recommend` | AI 选品推荐 | 5分钟 |
| `GET /api/lease-recommend` | AI 租赁推荐 | 5分钟 |
| `GET /api/search?q=` | 搜索饰品 | — |
| `GET /api/item/<id>` | 饰品详情 + 走势图 | — |
| `GET /api/backtest` | 回测报告 | — |
| `GET /api/cycle` | 轮询状态 | — |

## 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DASHSCOPE_API_KEY` | 阿里云百炼 API 密钥 | 必填 |
| `LLM_MODEL` | 大模型名称 | `qwen-max` |
| `LLM_TEMPERATURE` | 模型温度 | `0.7` |
| `MONITOR_URL` | 监控目标网址 | `https://csqaq.com` |
| `POLL_INTERVAL_SECONDS` | 轮询间隔（秒） | `300` |

## 回测

系统自动记录每次 AI 推荐，持续跟踪推荐后价格变化。回测引擎计算各策略（买入/观望/套利）的历史命中率。

## 常见问题

**Q: Port 8080 is in use**
> ```bash
> lsof -ti:8080 | xargs kill -9
> ```

**Q: AI 推荐返回 0 条**
> 确保 `DASHSCOPE_API_KEY` 有效且 `LLM_MODEL=qwen-max`。首次调用约 30-60 秒（两个阶段 LLM + Playwright 采集）。

**Q: playwright install chromium 下载慢**
> ```bash
> PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright playwright install chromium
> ```

## License

MIT
