<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="120" alt="JobRadar Logo" />

# JobRadar

**AI 驱动的职位搜索 Agent，专注德国与中国科技岗位**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg)](https://openclaw.ai)

*[OpenClaw](https://openclaw.ai) 技能插件 — 独立运行或嵌入任意 AI Agent*

</div>

---

## 🌍 语言版本

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

---

## 它是什么？

JobRadar 读取你的简历，在欧洲和中国多个招聘平台同时搜索职位，用大语言模型（LLM）对每个职位与你的匹配度进行打分，并自动生成每日摘要、Excel 追踪表和定制化求职信。

```
你的简历（Markdown 格式）
    │
    ▼
┌─────────────────────────────────────────────────┐
│  1. 发现   解析简历 → 提取目标岗位关键词         │
│            构建各平台专属搜索查询                │
├─────────────────────────────────────────────────┤
│  2. 抓取   联邦劳动局 · Indeed · Glassdoor ·    │
│            StepStone · BOSS直聘 · 拉勾网 ·      │
│            智联招聘（7 个来源）                  │
├─────────────────────────────────────────────────┤
│  3. 打分   LLM 从 6 个维度评分：                │
│            技能 · 级别 · 地点 · 语言 · 签证 ·  │
│            成长潜力                              │
├─────────────────────────────────────────────────┤
│  4. 交付   Excel 追踪表 · 每日摘要 ·            │
│            求职信 · 邮件推送                     │
└─────────────────────────────────────────────────┘
```

---

## ✨ 功能特性

| 功能 | 详情 |
|------|------|
| **7 个职位来源** | 联邦劳动局、Indeed、Glassdoor、StepStone、BOSS直聘、拉勾网、智联招聘 |
| **LLM 打分** | 每个职位 6 维度评分（0–10），附推理说明 |
| **支持任意 LLM** | 火山方舟、Z.AI、OpenAI、DeepSeek、OpenRouter、Ollama |
| **Excel 追踪表** | 单表，按分数颜色标注，支持标记已投递 |
| **每日摘要** | 最优匹配职位的 Markdown 摘要 |
| **求职信** | 按公司自动生成个性化求职信 |
| **邮件提醒** | SMTP 摘要推送（支持 Gmail 应用密码） |
| **增量更新** | 只对真正新增的职位评分，每日更新极快 |
| **反馈学习** | `--feedback "AMD liked"` 影响后续评分偏好 |
| **CLI + Agent** | 命令行工具，或嵌入 OpenClaw / Claude Code |

---

## 🚀 快速开始

```bash
# 1. 安装
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar
pip install -e .

# 2. 配置 LLM 密钥（任选其一）
export ARK_API_KEY=你的火山方舟密钥      # 火山方舟（豆包）
# export OPENAI_API_KEY=sk-…            # OpenAI
# export ZAI_API_KEY=…                  # Z.AI
# export DEEPSEEK_API_KEY=…             # DeepSeek

# 3. 运行配置向导（生成 config.yaml 和简历模板）
jobradar --setup

# 4. 将简历放入 cv/cv_current.md，然后：
jobradar --mode quick           # 快速测试（约 3 分钟）
jobradar                        # 完整流程
jobradar --install-agent        # 每天早 8 点自动执行
```

---

## 🔌 职位来源

### 欧洲（德国为主）

| 来源 | 平台 | 状态 |
|------|------|------|
| 联邦劳动局 | 德国官方招聘 | ✅ 可用 |
| Indeed DE | via python-jobspy | ✅ 可用 |
| Glassdoor DE | via python-jobspy | ✅ 可用 |
| StepStone | 德国招聘网站 | 🔧 开发中 |
| XING | DACH 职业社交 | 🔧 开发中 |

### 中国

| 来源 | 状态 | 备注 |
|------|------|------|
| BOSS直聘 | ✅ 可用 | 需要 Cookie 配置 |
| 拉勾网 | ✅ 可用 | 自动获取 Session |
| 智联招聘 | ✅ 可用 | 无需登录 |

在 `config.yaml` 的 `search.locations` 中加入中国城市即可激活中国来源：
```yaml
search:
  locations: ["Hannover", "Berlin", "上海", "北京", "深圳"]
```

---

## 🤖 支持的 LLM

系统启动时按优先级自动检测可用密钥：

| 优先级 | 提供商 | 环境变量 |
|--------|--------|----------|
| 1 | config.yaml 显式配置 | — |
| 2 | 火山方舟 | `ARK_API_KEY` |
| 3 | Z.AI | `ZAI_API_KEY` |
| 4 | OpenAI | `OPENAI_API_KEY` |
| 5 | DeepSeek | `DEEPSEEK_API_KEY` |
| 6 | OpenRouter | `OPENROUTER_API_KEY` |
| 7 | Ollama（本地） | 无需密钥 |

---

## 📊 评分维度

每个职位从 6 个维度评分（0–10），加权得出最终分数：

| 维度 | 说明 |
|------|------|
| **技能匹配** | 技术栈与岗位要求的重叠度 |
| **级别匹配** | 工作年限与岗位级别的匹配度 |
| **地点匹配** | 通勤距离 / 远程友好度 |
| **语言匹配** | 德语/英语要求与你的语言能力 |
| **签证友好** | 雇主提供工作许可的可能性 |
| **成长潜力** | 职业发展路径、领域相关性 |

---

## 🖥️ 命令参考

```bash
jobradar --setup                  # 交互式配置向导
jobradar                          # 完整流程（抓取 + 打分 + 输出）
jobradar --update                 # 增量更新（仅新增职位）
jobradar --mode quick             # 快速测试（约 3 分钟）
jobradar --mode dry-run           # 仅展示搜索查询，不执行
jobradar --install-agent          # 安装每日定时任务

# 对话式命令（适用于 AI Agent）
jobradar --show-digest            # 显示今日摘要
jobradar --generate-app "AMD"     # 生成 AMD 岗位求职信
jobradar --mark-applied "SAP"     # 标记 SAP 职位已投递
jobradar --explain "Databricks"   # 查看 Databricks 评分详情
jobradar --feedback "AMD liked"   # 记录偏好影响后续评分
```

---

## 🔑 BOSS直聘 Cookie 配置

1. 在 Chrome 中登录 [zhipin.com](https://www.zhipin.com)
2. 打开开发者工具 → **Application → Cookies → www.zhipin.com**
3. 复制 `__zp_stoken__` 和 `wt2` 的值
4. 设置环境变量：
   ```bash
   export BOSSZHIPIN_COOKIES="__zp_stoken__=xxx; wt2=yyy"
   ```

---

## 🧩 作为 OpenClaw 技能使用

JobRadar 是一个 [OpenClaw](https://openclaw.ai) 技能插件，可通过自然语言调用：

```
"在柏林搜索 AI 工程师职位，展示匹配度最高的 5 个"
"为 Databricks 职位生成一封求职信"
"把 SAP 的职位标记为已投递"
"今天的职位摘要是什么？"
```

---

## 🗺️ 路线图

- [ ] StepStone 完整爬虫
- [ ] XING 原生适配器
- [ ] 并行多源抓取（asyncio）
- [ ] `--status` 概览命令
- [ ] Web UI
- [ ] 前程无忧（51job）支持

---

## 📄 许可证

GNU 通用公共许可证 v3.0 — 详见 [LICENSE](LICENSE)

---

<div align="center">
为在德国和中国科技行业求职的朋友们用心打造 ❤️
</div>
