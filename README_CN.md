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

> **JobRadar** 读取你的简历，同时在德国与中国 7 个招聘平台并行搜索，用大语言模型从 6 个维度对每个职位打分，自动生成每日摘要、HTML 报告和个性化求职信。放入简历，告诉它往哪找，剩下的交给它。

---

<div align="center">

| 💬 交流与反馈 | ☕ 支持项目 |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="300" alt="微信公众号" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101825487.png" width="300" alt="微信支付 & 支付宝" /> |
| 扫码关注微信公众号 · 留言反馈 | 微信支付 · 支付宝 — 没有压力，点个 ⭐ 同样是支持 |

</div>

---

## ⚡ OpenClaw 零配置 — 一条消息搞定

如果你使用 [OpenClaw](https://openclaw.ai)，JobRadar 作为技能插件安装后**只需提供你的简历**——API Key 自动从 OpenClaw 环境检测，无需手动配置任何文件。

```bash
# 一次性技能安装
git clone https://github.com/jason-huanghao/jobradar.git ~/.agents/skills/jobradar
cd ~/.agents/skills/jobradar && python3 -m venv .venv && .venv/bin/pip install -e . -q
openclaw gateway restart
```

然后直接说：

```
帮我找德国的工作。我的简历：https://github.com/你/仓库/blob/main/cv.md
```

Agent 自动调用 `setup`（从 OpenClaw 配置检测 API Key）、抓取 36+ 职位、AI 打分，并将 HTML 报告发布到 GitHub Pages——**两轮对话，零配置文件**。

> 📄 效果示例：[report-539db1d2.html](https://jason-huanghao.github.io/jobradar/report-539db1d2.html)

---

## 📋 目录导航

| [✨ 功能特性](#-功能特性) | [⚙️ 工作原理](#️-工作原理) | [🚀 快速开始](#-快速开始) |
|:---:|:---:|:---:|
| [🤖 OpenClaw & Claude](#-使用-openclaw--claude) | [🔌 职位来源](#-职位来源) | [🔌 LLM 支持](#-llm-支持) |
| [⚙️ 配置说明](#️-配置说明) | [🖥️ 命令参考](#️-命令参考) | [📊 评分系统](#-评分系统) |
| [🗂️ 项目结构](#️-项目结构) | [🗺️ 路线图](#️-路线图) | [🤝 参与贡献](#-参与贡献) |

---

## ✨ 功能特性

| 功能 | 你能得到什么 |
|------|------------|
| 🌐 **7 个来源并行抓取** | 联邦劳动局、Indeed、Glassdoor、Google Jobs、StepStone、BOSS直聘、拉勾网、智联招聘——同时进行 |
| 🤖 **AI 匹配打分** | 6 维度评分（0–10）附完整推理——清楚知道为什么一个职位评分高 |
| 🔑 **零配置 API Key** | 自动从 OpenClaw 认证、Claude OAuth 或环境变量检测——无需手动填写 |
| 🔌 **任意 LLM，无锁定** | 火山方舟、Z.AI、OpenAI、DeepSeek、OpenRouter、Ollama——自动检测 |
| 📊 **HTML 报告 + Excel** | 颜色标注追踪表 + 一键发布到 GitHub Pages 的可分享报告 |
| 📰 **每日摘要** | Markdown 格式最优匹配简报，可推送手机或邮件 |
| ✉️ **定制求职信** | 按公司、按简历自动生成，不是套模板 |
| 📧 **邮件推送提醒** | SMTP 摘要推送（支持 Gmail 应用密码） |
| ⚡ **增量设计** | 只对新增职位评分——每日更新几分钟搞定 |
| 🧠 **学习你的偏好** | `--feedback "AMD liked"` 一条命令，影响所有后续评分 |

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
│           联邦劳动局 (DE) · Indeed · Glassdoor        │
│           Google Jobs · StepStone (DE)                │
│           BOSS直聘 · 拉勾网 · 智联招聘 (CN)          │
├──────────────────────────────────────────────────────┤
│ 3  过滤   URL 去重 · 过滤实习/噪音（LLM 前，免费）   │
├──────────────────────────────────────────────────────┤
│ 4  评分   LLM 从 6 个维度评分（0–10）：              │
│           技能 · 级别 · 地点 · 语言 · 签证 · 成长    │
├──────────────────────────────────────────────────────┤
│ 5  交付   📊 HTML 报告（GitHub Pages）               │
│           📰 每日 Markdown 摘要                       │
│           ✉️  每家公司定制求职信                      │
│           📧 邮件推送提醒                             │
└──────────────────────────────────────────────────────┘
         ↑
         └── 反馈循环：偏好记录自动影响后续所有评分
```

---

## 🚀 快速开始

**所需条件：** Python 3.11+、一个 LLM API Key、你的简历。

```bash
# 1 — 克隆并安装
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar && pip install -e .

# 2 — 配置 LLM 密钥（任选一个）
export ARK_API_KEY=你的火山方舟密钥    # 推荐国内用户
# export OPENAI_API_KEY=sk-…
# export DEEPSEEK_API_KEY=…           # 最经济实惠

# 3 — 一键初始化（自动生成 config.yaml）
jobradar --init --cv ./cv/cv_current.md --locations "上海,北京,Remote"

# 4 — 验证连接
jobradar --health

# 5 — 首次运行
jobradar --mode quick               # 约 3 分钟，2 个来源，用于测试
jobradar --update                   # 完整增量运行
jobradar --install-agent            # 设置每天早 8 点自动执行
```

---

## 🤖 使用 OpenClaw & Claude

### OpenClaw（推荐）

安装一次，直接对话。**API Key 自动从 OpenClaw 配置检测**——Agent 只需要你的简历 URL。

**日常使用对话映射：**

| 你说 | 执行内容 |
|------|---------|
| "帮我找德国的工作，简历：https://…" | `setup` + `run_pipeline` + `list_jobs` |
| "JobRadar 准备好了吗？" | `--health --json` |
| "今天有什么好职位？" | `--show-digest --json` |
| "给 SAP 写封求职信" | `--generate-app "SAP"` |
| "我投了 Zalando" | `--mark-applied "Zalando"` |
| "Databricks 为什么评分低？" | `--explain "Databricks"` |
| "发布我的职位报告" | `get_report --publish` → GitHub Pages 链接 |
| "设置每天自动搜索" | `--install-agent` |

### Claude Code / claude.ai

```bash
jobradar --init --cv ./cv.md --llm openai --key $OPENAI_API_KEY
jobradar --health && jobradar --mode quick
```

或直接说：*"帮我设置 JobRadar，找上海的 ML 岗位"*

---

## 🔌 职位来源

### 🇩🇪 德国 / 欧洲

| 来源 | 状态 | 认证要求 |
|------|------|---------|
| 联邦劳动局 | ✅ 可用 | 无 |
| Indeed DE | ✅ 可用 | 无 |
| Glassdoor DE | ✅ 可用 | 无 |
| Google Jobs | ✅ 可用 | 无 |
| StepStone | 🔧 开发中 | — |
| XING | 🔧 开发中 | Apify Token |

### 🇨🇳 中国

| 来源 | 状态 | 认证要求 |
|------|------|---------|
| BOSS直聘 | ✅ 可用 | 浏览器 Cookie + 国内 IP |
| 拉勾网 | ✅ 可用 | Session Cookie（自动获取） |
| 智联招聘 | ✅ 可用 | 无需登录（建议国内 IP） |

**BOSS直聘 Cookie 配置（一次性，约 2 分钟）：**
1. Chrome 登录 [zhipin.com](https://www.zhipin.com)
2. 开发者工具 → Application → Cookies → `www.zhipin.com`
3. 复制 `__zp_stoken__` 和 `wt2` 的值
4. `.env` 中添加：`BOSSZHIPIN_COOKIES="__zp_stoken__=xxx; wt2=yyy"`

---

## 🔌 LLM 支持

自动按优先级检测，**OpenClaw 用户通常无需任何操作**：

| 优先级 | 来源 | 环境变量 | 说明 |
|--------|------|----------|------|
| 0 | **OpenClaw 认证配置** | 自动 | 从 OpenClaw auth-profiles 读取 |
| 1 | **Claude OAuth** | 自动 | `~/.claude/.credentials.json` |
| 2 | `config.yaml` 显式配置 | — | 固定使用特定模型 |
| 3 | **火山方舟** | `ARK_API_KEY` | 豆包系列，国内用户首选 |
| 4 | **Z.AI** | `ZAI_API_KEY` | Z.AI 编程套餐 |
| 5 | **OpenAI** | `OPENAI_API_KEY` | 推荐 gpt-4o-mini |
| 6 | **DeepSeek** | `DEEPSEEK_API_KEY` | 最经济（约 ¥1/百万 tokens） |
| 7 | **OpenRouter** | `OPENROUTER_API_KEY` | 200+ 模型一个 key |
| 8 | **Ollama** | 无需 | 完全本地，自动检测 |

---

## ⚙️ 配置说明

```bash
cp config.example.yaml config.yaml   # 不要提交此文件
```

关键配置：
```yaml
candidate:
  cv: "./cv/cv_current.md"          # 支持 .md .pdf .docx 或 URL

search:
  locations: ["上海", "北京", "Remote"]
  max_days_old: 14
  exclude_keywords: ["实习", "intern", "Praktikum"]
  exclude_companies: ["前公司名称"]

scoring:
  min_score_digest: 6               # 出现在每日摘要的门槛
  min_score_application: 7          # 自动生成求职信的门槛

server:
  db_path: ./jobradar.db            # 本地路径，无 ~/.jobradar 泄漏
```

---

## 🖥️ 命令参考

```bash
# 初始化
jobradar --init [--cv 路径或URL] [--locations "城市1,城市2"] [--llm 提供商]
jobradar --health [--json]          # 连通性检查
jobradar --status [--json]          # 职位池统计

# 运行
jobradar --update                   # 日常使用：仅新增职位
jobradar --mode quick               # 快速测试（约 3 分钟）
jobradar --mode dry-run             # 只展示查询，不执行

# 对话式
jobradar --show-digest [--json]     # 今日最优职位
jobradar --generate-app "公司名"    # 生成求职信
jobradar --mark-applied "公司名"    # 标记已投递
jobradar --explain "公司名"         # 查看完整评分详情
jobradar --feedback "AMD liked"    # 记录偏好
jobradar --install-agent            # 设置每日定时任务
```

---

## 📊 评分系统

| 维度 | 评估内容 |
|------|---------|
| **技能匹配** | 技术栈与岗位要求的重叠度 |
| **级别匹配** | 工作年限与岗位级别的适配度 |
| **地点匹配** | 通勤可行性、远程友好度 |
| **语言匹配** | 德语/英语要求与你的实际语言能力 |
| **签证友好** | 雇主提供工作许可的可能性 |
| **成长潜力** | 职业发展路径、公司趋势、领域相关性 |

---

## 🗂️ 项目结构

```
jobradar/
├── src/jobradar/
│   ├── sources/              # 各平台适配器
│   ├── report/               # HTML 报告生成 + GitHub Pages 发布
│   ├── interfaces/
│   │   ├── skill.py          # OpenClaw 技能入口（零配置）
│   │   └── cli.py            # CLI 入口
│   ├── config.py             # 配置模型（所有路径相对化）
│   └── scorer.py             # LLM 批量评分引擎
├── SKILL.md                  # OpenClaw 技能清单
├── jobradar-skill            # Bash 入口脚本（自动加载 .env）
├── config.example.yaml       # 带注释的配置模板
└── tests/                    # 14/14 通过
```

---

## 🗺️ 路线图

- [x] 并行多源抓取
- [x] `--status` / `--health` / `--json` Agent 友好接口
- [x] OpenClaw 零配置（API Key 自动检测）
- [x] 自包含 HTML 报告 + GitHub Pages 发布
- [x] 所有路径相对化（无 `~/.jobradar` 泄漏）
- [ ] StepStone 完整爬虫
- [ ] XING / LinkedIn 适配器
- [ ] 前程无忧（51job）
- [ ] Docker 一键部署
- [ ] OpenClaw 定时 Cron 任务

---

## 🤝 参与贡献

欢迎贡献——尤其是招聘平台适配器和测试覆盖。

```bash
git clone https://github.com/jason-huanghao/jobradar.git
pip install -e ".[dev]"
ruff check src/ && pytest tests/ -v
```

---

## ⚠️ 免责声明

本项目仅用于**个人求职、技术学习和学术研究目的**。用户须遵守各平台 `robots.txt` 和服务条款，不得用于商业数据采集。

---

## 📄 许可证

GNU 通用公共许可证 v3.0 — 详见 [LICENSE](LICENSE)

---

<div align="center">

为在德国和中国科技行业求职的朋友们用心打造 ❤️

**⭐ 如果 JobRadar 帮你拿到了面试，点个 Star 是莫大的鼓励。**

</div>
