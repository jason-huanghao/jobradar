<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="140" alt="JobRadar Logo" />

# JobRadar

### 闇雲な応募はやめよう。AIが本当に合う求人を見つけてくれる。

[![GitHub Stars](https://img.shields.io/github/stars/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/network)
[![GitHub Issues](https://img.shields.io/github/issues/jason-huanghao/jobradar?style=flat-square)](https://github.com/jason-huanghao/jobradar/issues)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg?style=flat-square)](https://openclaw.ai)

*[OpenClaw](https://openclaw.ai) スキル — 単独実行またはAIエージェント組み込み可能*

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

</div>

---

> **JobRadar** は履歴書を読み込み、ドイツ・中国の**7つの求人サイト**を並列検索。LLMが各求人を6軸でスコアリングし、カバーレターとCV最適化セクションを自動生成。BOSS直聘・LinkedInへの**自動応募**まで対応します。

---

<div align="center">

| 💬 コミュニティ・フィードバック | ☕ プロジェクトを支援 |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101827472.png" width="300" alt="WeChat公式アカウント" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101825487.png" width="300" alt="WeChat Pay & Alipay" /> |
| WeChatをフォロー · フィードバック送信 | WeChat Pay · Alipay — ⭐でも大歓迎 |

</div>

---

## ⚡ OpenClawでゼロ設定 — メッセージ1件で完了

一度インストールすれば、**履歴書URLだけで動作します**。APIキーはOpenClaw環境から自動検出。

```bash
git clone https://github.com/jason-huanghao/jobradar.git ~/.agents/skills/jobradar
cd ~/.agents/skills/jobradar && python3 -m venv .venv && .venv/bin/pip install -e . -q
openclaw gateway restart
```

こう言うだけ：*"ドイツの求人を探して。私の履歴書：https://github.com/…"*

`setup` → 36件以上スクレイプ → AIスコアリング → GitHub PagesにHTMLレポート公開 — **1メッセージ、設定ファイル不要**。

> 📄 サンプル: [report-539db1d2.html](https://jason-huanghao.github.io/jobradar/report-539db1d2.html)

---

## ✨ 主な機能

| 機能 | 詳細 |
|------|------|
| 🌐 **7ソース並列クロール** | Bundesagentur、Indeed、Glassdoor、Google Jobs、StepStone、XING、BOSS直聘、拉勾网、智联招聘 |
| 🤖 **AIマッチングスコア** | 6軸スコア（0–10）＋完全な理由説明 |
| 🔑 **APIキー自動検出** | OpenClaw認証・Claude OAuth・環境変数から自動取得 |
| 🔌 **どのLLMでも対応** | Volcengine Ark、Z.AI、OpenAI、DeepSeek、OpenRouter、Ollama |
| ✉️ **カスタムカバーレター** | 企業ごと・CV対応・LLM生成（テンプレートではない） |
| 📝 **CVセクション最適化** | 各求人に合わせてサマリー＋スキルセクションを書き直す |
| 📊 **HTMLレポート + Excel** | GitHub Pages公開レポート＋カラーコードExcelトラッカー |
| 🚀 **自動応募** | BOSS直聘 Playwrightあいさつ + LinkedIn Easy Apply（`[apply]`エクストラ必要） |
| 🌐 **Webダッシュボード** | FastAPI UI — 求人閲覧・応募書類生成・Excelダウンロード |
| ⚡ **インクリメンタル設計** | 新規求人のみスコアリング — 毎日の更新が数分で完了 |

---

## ⚙️ 仕組み

```
あなたの履歴書（Markdown / PDF / DOCX / URL）
              │
              ▼
┌──────────────────────────────────────────────────┐
│ 1  発見    CV解析 → 目標職種・スキル・地域抽出   │
├──────────────────────────────────────────────────┤
│ 2  検索    7ソース並列：                         │
│            Bundesagentur · Indeed · Glassdoor    │
│            Google Jobs · StepStone · XING  (DE) │
│            BOSS直聘 · 拉勾网 · 智联招聘  (CN)   │
├──────────────────────────────────────────────────┤
│ 3  フィルタ URLで重複除去 · インターン除外       │
├──────────────────────────────────────────────────┤
│ 4  スコア  6軸評価（0–10）                       │
├──────────────────────────────────────────────────┤
│ 5  生成    ✉️  カバーレター · 📝 CVセクション    │
├──────────────────────────────────────────────────┤
│ 6  出力    📊 HTMLレポート · 📁 Excel            │
│            🌐 Webダッシュボード · 🚀 自動応募   │
└──────────────────────────────────────────────────┘
```

---

## 🚀 クイックスタート

```bash
# 1 — クローン & インストール
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar && pip install -e .
# CN: pip install -e ".[cn]"  自動応募: pip install -e ".[apply]"

# 2 — APIキー設定（1つでOK）
export OPENAI_API_KEY=sk-…
# export ARK_API_KEY=…  export DEEPSEEK_API_KEY=…

# 3 — セットアップウィザード
jobradar init
# 非対話型: jobradar init --cv ./cv.md --api-key ARK_API_KEY=xxx -y

# 4 — 接続確認
jobradar health

# 5 — 実行
jobradar run --mode quick    # ~3分テスト
jobradar run                  # フル実行
jobradar install-agent        # 毎朝8時自動化（macOS）
```

---

## 🔌 求人ソース

DEソースはすべて**完全実装済み**（認証・Playwright不要）:

| ソース | 認証 | 備考 |
|--------|------|------|
| Bundesagentur für Arbeit | 不要 | 連邦雇用API |
| Indeed DE | 不要 | via python-jobspy |
| Glassdoor DE | 不要 | via python-jobspy |
| Google Jobs | 不要 | via python-jobspy |
| StepStone | 不要 | httpx + BeautifulSoupスクレイパー |
| XING | 不要 | httpx + BeautifulSoupスクレイパー |
| BOSS直聘（中国） | Cookie | `BOSSZHIPIN_COOKIES` 必要 · `[cn]`エクストラ |
| 拉勾网（中国） | 不要 | モバイルAPI → AJAX → Playwright |
| 智联招聘（中国） | 不要 | REST API → Playwrightフォールバック |

---

## 🔌 LLMプロバイダー

優先順に自動検出：

| 優先度 | ソース | 環境変数 |
|--------|--------|---------|
| 0 | **OpenClaw auth-profiles** | 自動 |
| 1 | **Claude OAuth** | 自動 |
| 2 | Volcengine Ark | `ARK_API_KEY` |
| 3 | Z.AI / OpenAI / DeepSeek | 各環境変数 |
| 4 | OpenRouter | `OPENROUTER_API_KEY` |
| 5 | Ollama / LM Studio | 不要（ローカル） |

---

## 🖥️ CLIリファレンス

```bash
jobradar init [--cv …] [--api-key ENV=val] [-y]
jobradar health / status
jobradar run [--mode quick|dry-run|score-only] [--limit N]
jobradar report [--publish] [--min-score 7]
jobradar apply [--dry-run] [--auto] [--min-score 8]
jobradar web [--port 8080]
jobradar install-agent
```

---

## 📊 スコアリングシステム

| 軸 | 評価内容 |
|----|---------|
| **スキルマッチ** | 技術スタックと求人要件の一致度 |
| **職級適合** | 経験年数とロールレベルの整合性 |
| **場所適合** | 通勤可否・リモートワーク対応 |
| **言語適合** | DE/EN要件と実際の語学力 |
| **ビザフレンドリー** | 労働許可スポンサーの見込み |
| **成長ポテンシャル** | キャリアパス・企業成長性 |

---

## 🤖 自動応募

必要: `pip install -e ".[apply]" && playwright install chromium`

**BOSS直聘**: 求人ページを開き、HR活動状況確認（7日超不活性→スキップ）、立即沟通クリック、カスタマイズ可能なあいさつ送信。ランダム遅延3–8秒、上限50件/日。

**LinkedIn Easy Apply**: Easy Applyボタンクリック、単一ステップ申請のみ提出（複数ステップはスキップ）。ランダム遅延4–10秒、上限25件/日。

```bash
jobradar apply --dry-run            # まずプレビュー
jobradar apply --auto --min-score 8 # 本番応募
```

---

## 🗺️ ロードマップ

- [x] 7ソース並列 · AI 6次元スコアリング · カバーレター + CV最適化
- [x] StepStone & XING 完全実装
- [x] BOSS直聘自動応募 + LinkedIn Easy Apply
- [x] HTMLレポート + GitHub Pages · Excelエクスポート · Webダッシュボード
- [x] OpenClaw ゼロ設定
- [ ] 前程无忧（51job）· Telegram/メールデイリー配信 · Docker · MCPサーバー

---

## ⚠️ 免責事項

本プロジェクトは**個人の求職活動・技術学習・学術研究のみ**を目的としています。各プラットフォームの`robots.txt`と利用規約を遵守してください。

---

## 📄 ライセンス

GNU General Public License v3.0 — [LICENSE](LICENSE) 参照

---

<div align="center">

ドイツと中国のテック市場で求職する方々のために ❤️

**⭐ JobRadarで面接を獲得できたなら、スターをいただけると励みになります。**

</div>
