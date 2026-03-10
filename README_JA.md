<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="140" alt="JobRadar Logo" />

# JobRadar

### 闇雲な応募はやめよう。AIが本当に合う求人を見つけてくれる。

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=flat-square)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg?style=flat-square)](https://openclaw.ai)

*[OpenClaw](https://openclaw.ai) スキル — 単独実行またはAIエージェント組み込み可能*

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

</div>

---

> **JobRadar** は履歴書を読み込み、ドイツ・中国の7つの求人サイトを並列検索。LLMが各求人を6軸でスコアリングし、毎日のダイジェスト・Excelトラッカー・カバーレターを全自動生成します。CVを入れて検索先を設定するだけ、あとは任せてください。

---

<div align="center">

| 💬 コミュニティ・フィードバック | ☕ プロジェクトを支援 |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101718363.png" width="160" alt="WeChat公式アカウント" /> | <img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101748931.png" width="300" alt="WeChat Pay & Alipay" /> |
| WeChatをフォロー · フィードバック送信 | WeChat Pay · Alipay — ⭐でも大歓迎 |

</div>

---

## 📋 ナビゲーション

| [✨ 主な機能](#-主な機能) | [⚙️ 仕組み](#️-仕組み) | [🚀 クイックスタート](#-クイックスタート) |
|:---:|:---:|:---:|
| [🤖 OpenClaw & Claude](#-openclaw--claude-で使う) | [🔌 求人ソース](#-求人ソース) | [🔌 LLMプロバイダー](#-llmプロバイダー) |
| [⚙️ 設定](#️-設定) | [🖥️ CLIリファレンス](#️-cliリファレンス) | [📊 スコアリング](#-スコアリングシステム) |
| [🗺️ ロードマップ](#️-ロードマップ) | [🤝 コントリビュート](#-コントリビュート) | [⚠️ 免責事項](#️-免責事項) |

---

## ✨ 主な機能

| 機能 | 詳細 |
|------|------|
| 🌐 **7ソース並列クロール** | 連邦雇用エージェンシー、Indeed、Glassdoor、Google Jobs、StepStone、BOSS直聘、拉勾网、智联招聘 — 同時実行 |
| 🤖 **AIマッチングスコア** | 6軸スコア（0–10）＋完全な理由説明 — なぜ高スコアかが分かる |
| 🔌 **どのLLMでも対応** | Volcengine Ark、Z.AI、OpenAI、DeepSeek、OpenRouter、Ollama — 環境変数から自動検出 |
| 📊 **Excelトラッカー** | スコア別カラーコード、応募状況、投稿日付 — 1ファイルで完結 |
| 📰 **毎日ダイジェスト** | トップマッチのMarkdownサマリーをメールやスマホに配信 |
| ✉️ **カスタムカバーレター** | 企業ごと・CV対応・LLM生成 — テンプレートではない |
| ⚡ **インクリメンタル設計** | 新規求人のみスコアリング — 毎日の更新が数分で完了 |
| 🧠 **好みを学習** | `--feedback "AMD liked"` — 1コマンドで将来のスコアリングを調整 |

---

## ⚙️ 仕組み

```
あなたの履歴書（Markdown / PDF / DOCX / URL）
              │
              ▼
┌──────────────────────────────────────────────────┐
│ 1  発見    CV解析 → 目標職種・スキル・地域抽出   │
│            プラットフォーム別クエリ生成          │
├──────────────────────────────────────────────────┤
│ 2  検索    7ソースを並列スレッドで実行           │
│            連邦雇用エージェンシー · Indeed ·     │
│            Glassdoor · BOSS直聘 · 拉勾网         │
├──────────────────────────────────────────────────┤
│ 3  フィルタ URLで重複除去 · インターン除外       │
│            （LLM前の無料フィルタ）               │
├──────────────────────────────────────────────────┤
│ 4  スコア  6軸評価（0–10）：                     │
│            スキル · 職級 · 場所 · 言語 ·        │
│            ビザ · 成長ポテンシャル               │
├──────────────────────────────────────────────────┤
│ 5  出力    Excel · 日次ダイジェスト ·            │
│            カバーレター · メール通知             │
└──────────────────────────────────────────────────┘
```

---

## 🚀 クイックスタート

```bash
# 1 — クローン & インストール
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar && pip install -e .

# 2 — LLMキーを設定（1つでOK）
export OPENAI_API_KEY=sk-…          # OpenAI
# export DEEPSEEK_API_KEY=…         # DeepSeek（最もコスト効率が良い）
# export ARK_API_KEY=…              # Volcengine Ark

# 3 — セットアップ（config.yamlを自動生成）
jobradar --init --cv ./cv/cv_current.md --locations "東京,Remote"

# 4 — 接続確認
jobradar --health

# 5 — 初回実行
jobradar --mode quick               # ~3分、2ソース — テスト向け
jobradar --update                   # フル増分実行
jobradar --install-agent            # 毎朝8時に自動化
```

---

## 🤖 OpenClaw & Claude で使う

| あなたの発言 | 実行されるコマンド |
|------------|-----------------|
| 「JobRadarを設定して。CVはhttps://…」 | `jobradar --init --cv … --llm … --key …` |
| 「JobRadarは準備できてる?」 | `jobradar --health --json` |
| 「AI系の求人を探して」 | `jobradar --mode quick` |
| 「今日のトップ求人を見せて」 | `jobradar --show-digest --json` |
| 「DeepLのカバーレターを作って」 | `jobradar --generate-app "DeepL"` |
| 「SAPに応募した」 | `jobradar --mark-applied "SAP"` |
| 「Databricksはなぜ低スコア?」 | `jobradar --explain "Databricks"` |

---

## 🔌 求人ソース

| ソース | ステータス | 認証 |
|--------|-----------|------|
| 連邦雇用エージェンシー | ✅ 有効 | 不要 |
| Indeed DE | ✅ 有効 | 不要 |
| Glassdoor DE | ✅ 有効 | 不要 |
| Google Jobs | ✅ 有効 | 不要 |
| StepStone | 🔧 開発中 | — |
| XING | 🔧 開発中 | Apifyトークン |
| BOSS直聘（中国） | ✅ 有効 | Cookie + 中国IP |
| 拉勾网（中国） | ✅ 有効 | Session Cookie（自動） |
| 智联招聘（中国） | ✅ 有効 | 不要 |

---

## 🔌 LLMプロバイダー

| プロバイダー | 環境変数 | 備考 |
|-------------|---------|------|
| Volcengine Ark | `ARK_API_KEY` | doubauシリーズ |
| Z.AI | `ZAI_API_KEY` | — |
| OpenAI | `OPENAI_API_KEY` | gpt-4o-mini推奨 |
| DeepSeek | `DEEPSEEK_API_KEY` | 最もコスト効率が良い |
| OpenRouter | `OPENROUTER_API_KEY` | 200以上のモデル |
| Ollama | 不要 | 完全ローカル |

---

## ⚙️ 設定

```yaml
candidate:
  cv_path: "./cv/cv_current.md"
search:
  locations: ["Berlin", "Remote", "東京"]
  exclude_keywords: ["Praktikum", "internship", "インターン"]
scoring:
  min_score_digest: 6
  min_score_application: 7
```

---

## 🖥️ CLIリファレンス

```bash
jobradar --init [--cv …] [--locations …] [--llm …] [--key …]
jobradar --health [--json]          # 接続チェック
jobradar --status [--json]          # プール統計
jobradar --update                   # 日次実行（新規求人のみ）
jobradar --mode quick               # クイックテスト（~3分）
jobradar --show-digest [--json]     # 今日のトップ求人
jobradar --generate-app "会社名"    # カバーレター生成
jobradar --mark-applied "会社名"    # 応募済みマーク
jobradar --explain "会社名"         # スコア詳細表示
jobradar --feedback "AMD liked"    # 好みを記録
jobradar --install-agent            # 毎日の自動化設定
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

## 🗺️ ロードマップ

- [x] 並列クロール（ThreadPoolExecutor）
- [x] `--status` / `--health` / `--json`
- [x] `--init` 非インタラクティブセットアップ
- [x] ネガティブキーワード & 企業フィルター
- [ ] StepStone完全実装
- [ ] XINGネイティブアダプター
- [ ] Dockerワンライナー

---

## 🤝 コントリビュート

```bash
git clone https://github.com/jason-huanghao/jobradar.git
pip install -e ".[dev]"
ruff check src/ && pytest tests/ -v
```

---

## ⚠️ 免責事項

本プロジェクトは**個人的な求職活動・技術学習・学術研究のみ**を目的としています。各プラットフォームの`robots.txt`と利用規約を遵守してください。

---

## 📄 ライセンス

GNU General Public License v3.0 — [LICENSE](LICENSE) 参照

---

<div align="center">

ドイツと中国のテック市場で活躍する求職者のために ❤️

**⭐ JobRadarで面接につながったなら、スターをいただけると励みになります。**

</div>
