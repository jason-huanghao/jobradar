<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="140" alt="JobRadar Logo" />

# JobRadar

### 告别盲目海投，让 AI 替你找对的工作

[![GitHub Stars](https://img.shields.io/github/stars/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/network)
[![GitHub Issues](https://img.shields.io/github/issues/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/issues)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg?style=flat-square)](https://openclaw.ai)

*[OpenClaw](https://openclaw.ai) 技能插件 — 独立运行或嵌入任意 AI Agent*

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

</div>

---

> **JobRadar** 读取你的简历，同时在德国与中国 7 个招聘平台并行搜索，用大语言模型从 6 个维度对每个职位与你的匹配度打分，自动生成每日摘要、Excel 追踪表和个性化求职信。放入简历，告诉它往哪找，剩下的交给它。

---

<div align="center">

| 💬 交流与反馈 | ☕ 支持项目 |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101718363.png" width="160" alt="微信公众号" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101748931.png" width="300" alt="微信支付 & 支付宝" /> |
| 扫码关注微信公众号 · 留言反馈 | 微信支付 · 支付宝 — 没有压力，点个 ⭐ 同样是支持 |

</div>

---

## 📋 目录导航

| [✨ 功能特性](#-功能特性) | [⚙️ 工作原理](#️-工作原理) | [🚀 快速开始](#-快速开始) |
|:---:|:---:|:---:|
| [🤖 OpenClaw & Claude 用法](#-使用-openclaw--claude) | [🔌 职位来源](#-职位来源) | [🔌 LLM 支持](#-llm-支持) |
| [⚙️ 配置说明](#️-配置说明) | [🖥️ 命令参考](#️-命令参考) | [📊 评分系统](#-评分系统) |
| [🗺️ 路线图](#️-路线图) | [🤝 参与贡献](#-参与贡献) | [⚠️ 免责声明](#️-免责声明) |

---

## ✨ 功能特性

| 功能 | 你能得到什么 |
|------|------------|
| 🌐 **7 个来源并行抓取** | 联邦劳动局、Indeed、Glassdoor、Google Jobs、StepStone、BOSS直聘、拉勾网、智联招聘——同时进行 |
| 🤖 **AI 匹配打分** | 6 维度评分（0–10）附完整推理说明——清楚知道为什么一个职位评分高 |
| 🔌 **任意 LLM，无锁定** | 火山方舟、Z.AI、OpenAI、DeepSeek、OpenRouter、Ollama——从环境变量自动检测 |
| 📊 **Excel 追踪表** | 按分数颜色标注，含投递状态、发布日期——一张表，信息全覆盖 |
| 📰 **每日摘要** | Markdown 格式的最优匹配简报，可推送手机或邮件 |
| ✉️ **定制求职信** | 按公司、按简历自动生成，不是套模板 |
| 📧 **邮件推送提醒** | SMTP 摘要推送（支持 Gmail 应用密码） |
| ⚡ **增量设计** | 只对真正新增的职位评分——每日更新几分钟搞定 |
| 🧠 **学习你的偏好** | `--feedback "AMD liked"` 一条命令，影响所有后续评分 |
| 🤝 **对话式 + Agent 就绪** | CLI、OpenClaw、Claude Code、claude.ai 均可使用 |

---

## ⚙️ 工作原理

```
你的简历（Markdown / PDF / DOCX / URL）
              │
              ▼
┌──────────────────────────────────────────────────────┐
│ 1  发现   LLM 解析简历 → 提取目标岗位、技能、地点    │
│           构建各平台专属搜索查询                      │
├──────────────────────────────────────────────────────┤
│ 2  抓取   7 个来源并行抓取                           │
│           联邦劳动局 (DE)                             │
│           Indeed · Glassdoor · Google Jobs            │
│           StepStone (DE)                              │
│           BOSS直聘 · 拉勾网 · 智联招聘 (CN)          │
├──────────────────────────────────────────────────────┤
│ 3  过滤   URL 去重 · 关键词过滤实习/噪音             │
│           （在 LLM 评分之前，免费且快速）             │
├──────────────────────────────────────────────────────┤
│ 4  评分   LLM 从 6 个维度评分（0–10）：              │
│           技能 · 级别 · 地点 · 语言 · 签证 · 成长    │
├──────────────────────────────────────────────────────┤
│ 5  交付   📊 Excel 追踪表（颜色标注）                │
│           📰 每日 Markdown 摘要                       │
│           ✉️  每家公司定制求职信                      │
│           📧 邮件推送提醒                             │
└──────────────────────────────────────────────────────┘
         ↑
         └── 反馈循环：你的偏好记录会自动
             影响后续所有评分
```

---

## 🚀 快速开始

**所需条件：** Python 3.11+、一个 LLM API Key、你的简历。

```bash
# 1 — 克隆并安装
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar && pip install -e .

# 2 — 配置 LLM 密钥（任选一个）
export ARK_API_KEY=你的火山方舟密钥    # 火山方舟（推荐国内用户）
# export OPENAI_API_KEY=sk-…          # OpenAI
# export DEEPSEEK_API_KEY=…           # DeepSeek（最经济实惠）
# export ZAI_API_KEY=…                # Z.AI

# 3 — 一键初始化（自动生成 config.yaml）
jobradar --init --cv ./cv/cv_current.md --locations "上海,北京,Remote"

# 4 — 验证连接
jobradar --health

# 5 — 首次运行
jobradar --mode quick               # 约 3 分钟，2 个来源，用于测试
jobradar --update                   # 完整增量运行
jobradar --install-agent            # 设置每天早 8 点自动执行
```

> 💡 **已在 AI Agent 里？** 直接说 *"帮我设置 JobRadar，我的简历在 https://…，OpenAI Key 是 sk-…"*，OpenClaw 或 Claude Code 会自动运行 `--init`，无需编辑任何文件。

---

## 🤖 使用 OpenClaw & Claude

JobRadar 专为对话式操作设计——说你想要什么，Agent 运行正确的命令。

### 选项 A — OpenClaw

将 `jobradar/` 放入 OpenClaw 技能目录，OpenClaw 自动读取 `SKILL.md`。

**零配置上手——一条消息搞定：**
```
你：帮我设置 JobRadar。我的简历在 https://mysite.com/cv.pdf，
    想找上海和北京的 AI/ML 职位，OpenAI Key 是 sk-xxxx
```
OpenClaw 自动运行 `jobradar --init …`，写入 `config.yaml` 和 `.env`，确认完成。

**日常使用对话映射：**

| 你说 | 执行命令 |
|------|---------|
| "JobRadar 准备好了吗？" | `jobradar --health --json` |
| "我的职位池现在有多少？" | `jobradar --status --json` |
| "帮我搜一下 AI 岗位" | `jobradar --mode quick` |
| "今天有什么好职位？" | `jobradar --show-digest --json` |
| "给 DeepL 写封求职信" | `jobradar --generate-app "DeepL"` |
| "我投了 Zalando" | `jobradar --mark-applied "Zalando"` |
| "Databricks 为什么评分低？" | `jobradar --explain "Databricks"` |
| "设置每天自动搜索" | `jobradar --install-agent` |

### 选项 B — Claude Code

在项目目录打开，Claude Code 自动读取 `CLAUDE.md`。
```bash
jobradar --init --cv ./cv.md --llm openai --key $OPENAI_API_KEY
jobradar --health && jobradar --mode quick
```
或直接说：*"帮我设置 JobRadar，找上海的 ML 岗位"*

### 最小配置（13 行，`--init` 自动生成）

```yaml
candidate:
  cv_url: "https://mysite.com/cv.pdf"   # 或 cv_path: "./cv/cv.md"
llm:
  text:
    provider: "openai"
    model: "gpt-4o-mini"
    api_key_env: "OPENAI_API_KEY"
search:
  locations: ["上海", "北京", "Remote"]
sources:
  arbeitsagentur: { enabled: true }
  jobspy: { enabled: true, boards: ["indeed", "google"], country: "germany" }
```

> 📖 完整指南：[docs/GUIDE_OPENCLAW_CLAUDE.md](docs/GUIDE_OPENCLAW_CLAUDE.md)

---

## 🔌 职位来源

### 🇩🇪 欧洲（德国为主）

| 来源 | 平台 | 状态 | 认证要求 |
|------|------|------|---------|
| **联邦劳动局** | 德国官方招聘 | ✅ 可用 | 无 |
| **Indeed DE** | 全球招聘 | ✅ 可用 | 无 |
| **Glassdoor DE** | 招聘 + 公司评价 | ✅ 可用 | 无 |
| **Google Jobs** | 聚合全球 | ✅ 可用 | 无 |
| **StepStone** | 德国高端招聘 | 🔧 开发中 | — |
| **XING** | DACH 职业社交 | 🔧 开发中 | Apify Token |

### 🇨🇳 中国

| 来源 | 状态 | 认证要求 |
|------|------|---------|
| **BOSS直聘** | ✅ 可用 | 浏览器 Cookie + 国内 IP |
| **拉勾网** | ✅ 可用 | Session Cookie（自动获取） |
| **智联招聘** | ✅ 可用 | 无需登录（建议国内 IP） |

> **国内平台说明：** 从欧洲访问建议使用 VPN 或部署在国内云服务器（如阿里云 ECS）以获得最佳效果。

**启用中国来源：**
```yaml
search:
  locations: ["柏林", "Remote", "上海", "北京"]
sources:
  zhilian:    { enabled: true }
  lagou:      { enabled: true }
  bosszhipin: { enabled: true }
```

**BOSS直聘 Cookie 配置（一次性，约 2 分钟）：**
1. Chrome 登录 [zhipin.com](https://www.zhipin.com)
2. 开发者工具 → Application → Cookies → `www.zhipin.com`
3. 复制 `__zp_stoken__` 和 `wt2`
4. `.env` 中添加：`BOSSZHIPIN_COOKIES="__zp_stoken__=xxx; wt2=yyy"`

---

## 🔌 LLM 支持

启动时自动检测第一个可用密钥——**已在 Agent 环境中的用户无需任何额外配置**。

| 优先级 | 提供商 | 环境变量 | 说明 |
|--------|--------|----------|------|
| 1 | `config.yaml` 显式配置 | — | 固定使用特定模型 |
| 2 | **火山方舟** | `ARK_API_KEY` | 豆包系列，国内用户首选 |
| 3 | **Z.AI** | `ZAI_API_KEY` | Z.AI 编程套餐 |
| 4 | **OpenAI** | `OPENAI_API_KEY` | 推荐 gpt-4o-mini |
| 5 | **DeepSeek** | `DEEPSEEK_API_KEY` | 最经济（约 ¥1/百万 tokens） |
| 6 | **OpenRouter** | `OPENROUTER_API_KEY` | 200+ 模型一个 key |
| 7 | **Ollama** | 无需 | 完全本地，自动检测 |

---

## ⚙️ 配置说明

```bash
cp config.example.yaml config.yaml   # 不要提交此文件
```

关键配置一览：
```yaml
candidate:
  cv_path: "./cv/cv_current.md"     # 支持 .md、.pdf、.docx 或 cv_url: https://…

search:
  locations: ["上海", "北京", "Remote"]
  max_days_old: 14
  exclude_keywords: ["实习", "intern", "Praktikum"]  # 评分前过滤，免费
  exclude_companies: ["前公司名称"]                   # 完全跳过

scoring:
  min_score_digest: 6                # 出现在每日摘要的门槛
  min_score_application: 7           # 自动生成求职信的门槛
```

完整带注释版本：[`config.example.yaml`](config.example.yaml)

---

## 🖥️ 命令参考

```bash
# ── 初始化 ────────────────────────────────────────────────────────
jobradar --init [--cv 路径或URL] [--locations "城市1,城市2"] [--llm 提供商] [--key KEY]
jobradar --setup                   # 交互式配置向导
jobradar --install-agent           # 安装每日定时任务

# ── 状态检查（Agent 友好）─────────────────────────────────────────
jobradar --health [--json]         # LLM + 来源连通性检查
jobradar --status [--json]         # 职位池统计 + 来源就绪状态

# ── 流水线 ────────────────────────────────────────────────────────
jobradar --update                  # ★ 日常使用：仅新增职位 + 邮件
jobradar                           # 完整流水线（抓取 + 评分 + 输出）
jobradar --mode quick              # 快速测试：2 个来源，约 3 分钟
jobradar --mode dry-run            # 只展示查询，不执行
jobradar --cv 路径或URL            # 本次运行使用指定简历

# ── 对话式命令 ────────────────────────────────────────────────────
jobradar --show-digest [--json]    # 今日最优职位
jobradar --generate-app "公司名"   # 生成求职信
jobradar --mark-applied "公司名"   # 标记已投递
jobradar --explain "公司名"        # 查看完整评分详情
jobradar --feedback "AMD liked"   # 记录偏好，影响后续评分
```

> 加 `--json` 后，`--status`、`--health`、`--show-digest` 的输出为纯 JSON（标准输出），横幅信息输出到标准错误——方便 Agent 直接解析。

---

## 📊 评分系统

每个职位独立从 6 个维度评分（0–10），加权得出最终分数：

| 维度 | 评估内容 |
|------|---------|
| **技能匹配** | 技术栈与岗位要求的重叠度 |
| **级别匹配** | 工作年限与岗位级别的适配度 |
| **地点匹配** | 通勤可行性、远程友好度、是否需要搬迁 |
| **语言匹配** | 德语/英语要求与你的实际语言能力 |
| **签证友好** | 雇主提供工作许可的可能性 |
| **成长潜力** | 职业发展路径、公司趋势、领域相关性 |

分数 ≥ `min_score_digest` → 出现在每日摘要  
分数 ≥ `min_score_application` → 自动生成求职信

---

## 🗺️ 路线图

- [x] 并行多源抓取（ThreadPoolExecutor）
- [x] `--status` / `--health` / `--json` Agent 友好接口
- [x] `--init` 非交互式初始化
- [x] 负面关键词 & 公司过滤
- [x] 从 URL 读取简历（PDF / HTML / Markdown / DOCX）
- [ ] StepStone 完整爬虫
- [ ] XING 原生适配器
- [ ] `--preview-score` 调试 Prompt
- [ ] 前程无忧（51job）支持
- [ ] MCP 服务模式（`jobradar serve`）
- [ ] Docker 一键部署

---

## 🤝 参与贡献

欢迎贡献——尤其是招聘平台适配器和测试覆盖。

```bash
git clone https://github.com/jason-huanghao/jobradar.git
pip install -e ".[dev]"
ruff check src/ && pytest tests/ -v
```

优先领域：StepStone / XING / LinkedIn 完整爬虫、`tests/` 测试覆盖、多语言 README 改进。

---

## ⚠️ 免责声明

本项目仅用于**个人求职、技术学习和学术研究目的**。

- 用户须遵守各平台的 `robots.txt` 和服务条款
- 不得用于批量商业数据采集或再分发
- 用户自行承担使用本工具的一切法律责任
- 本项目与任何招聘平台无关联

---

## 📄 许可证

GNU 通用公共许可证 v3.0 — 详见 [LICENSE](LICENSE)

---

<div align="center">

为在德国和中国科技行业求职的朋友们用心打造 ❤️

**⭐ 如果 JobRadar 帮你拿到了面试，点个 Star 是莫大的鼓励。**

</div>
