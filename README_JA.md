<div align="center">

<img src="https://raw.githubusercontent.com/jason-huanghao/PicGoBed/master/imgs/202603101124697.png" width="120" alt="JobRadar Logo" />

# JobRadar

**ドイツ・中国のIT求人に特化したAI求職エージェント**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-orange.svg)](https://openclaw.ai)

*[OpenClaw](https://openclaw.ai) スキル — 単独実行またはAIエージェント組み込み可能*

</div>

---

## 🌍 言語

[English](README.md) · [中文](README_CN.md) · [Deutsch](README_DE.md) · [日本語](README_JA.md) · [Español](README_ES.md) · [Français](README_FR.md)

---

## 概要

JobRadarは履歴書（CV）を読み込み、ヨーロッパと中国の複数求人サイトを同時に検索。LLMが各求人を6軸でスコアリングし、毎日のダイジェスト・Excelトラッカー・カバーレターを自動生成します。

```
あなたの履歴書（Markdown）
    │
    ▼
┌──────────────────────────────────────────────────┐
│  1. 発見    CV解析 → 目標職種の抽出              │
│             プラットフォーム別クエリ生成         │
├──────────────────────────────────────────────────┤
│  2. 検索    連邦雇用エージェンシー · Indeed ·    │
│             Glassdoor · StepStone ·              │
│             BOSS直聘 · 拉勾网 · 智联招聘         │
├──────────────────────────────────────────────────┤
│  3. スコア  6軸評価（各0〜10点）：               │
│             スキル · 職級 · 場所 · 言語 ·       │
│             ビザ · 成長ポテンシャル              │
├──────────────────────────────────────────────────┤
│  4. 出力    Excel · 日次ダイジェスト ·           │
│             カバーレター · メール通知            │
└──────────────────────────────────────────────────┘
```

---

## ✨ 主な機能

| 機能 | 詳細 |
|------|------|
| **7つの求人ソース** | 連邦雇用エージェンシー、Indeed、Glassdoor、StepStone、BOSS直聘、拉勾网、智联招聘 |
| **LLMスコアリング** | 6軸スコア（0〜10）＋理由説明 |
| **LLM自由選択** | Volcengine Ark、Z.AI、OpenAI、DeepSeek、OpenRouter、Ollama |
| **Excelトラッカー** | スコア別カラーコード、応募状況管理 |
| **日次ダイジェスト** | 上位マッチ求人のMarkdownサマリー |
| **カバーレター** | 企業別に自動生成・カスタマイズ |
| **メール通知** | SMTPダイジェスト（Gmail アプリパスワード対応） |
| **増分更新** | 新規求人のみスコアリング、高速な毎日更新 |
| **フィードバック学習** | `--feedback "AMD liked"` で将来のスコアリングを調整 |

---

## 🚀 クイックスタート

```bash
# 1. インストール
git clone https://github.com/jason-huanghao/jobradar.git
cd jobradar
pip install -e .

# 2. LLMキーを設定（いずれか1つ）
export ARK_API_KEY=your_key         # Volcengine Ark
# export OPENAI_API_KEY=sk-…        # OpenAI
# export DEEPSEEK_API_KEY=…         # DeepSeek

# 3. セットアップウィザードを実行
jobradar --setup

# 4. cv/cv_current.md に履歴書を配置して実行
jobradar --mode quick              # クイックテスト（約3分）
jobradar                           # フルパイプライン
jobradar --install-agent           # 毎日午前8時に自動実行
```

---

## 🖥️ CLIリファレンス

```bash
jobradar --setup                  # セットアップウィザード
jobradar                          # フルパイプライン
jobradar --update                 # 増分更新（新着求人のみ）
jobradar --mode quick             # クイックテスト
jobradar --install-agent          # 定期実行スケジューラー設定

# 会話型コマンド（AIエージェント用）
jobradar --show-digest            # 今日のダイジェスト表示
jobradar --generate-app "AMD"     # AMDポジション用カバーレター生成
jobradar --mark-applied "SAP"     # SAP求人を応募済みにマーク
jobradar --explain "Databricks"   # Databricksのスコア内訳を表示
jobradar --feedback "AMD liked"   # 好みを記録してスコアを調整
```

---

## 📊 スコアリング軸

| 軸 | 説明 |
|----|------|
| **スキルマッチ** | 技術スタックと求人要件の一致度 |
| **職級適合** | 経験年数と役職レベルの整合性 |
| **場所適合** | 通勤距離・リモートワーク可否 |
| **言語適合** | ドイツ語/英語要件と語学力 |
| **ビザフレンドリー** | スポンサーシップの見込み |
| **成長ポテンシャル** | キャリアパスとドメイン関連性 |

---

## 📄 ライセンス

GNU General Public License v3.0 — [LICENSE](LICENSE) 参照

---

<div align="center">
ドイツと中国のテック市場で活躍する求職者のために ❤️
</div>
