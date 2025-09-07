# 01 初期化: プロジェクト開始

## 最初に質問（実行前に回答してください）
- プログラム名（カテゴリ）（必須・例: Tools）
- プロジェクト名（必須・例: cursor_chat_history_exporter）
- プロジェクト目的（必須）
- 開始予定日/終了予定日（任意）

## 目的
Rules（`basic/00_master_rules.mdc`・`01_pmbok_initiating.mdc`）に準拠し、プロジェクトの基本構造（Stock/Flow配下）とドラフト文書（憲章/ステークホルダー）を作成します。

## 必要入力
- プログラム名: 例）`Tools`（プロジェクトのカテゴリ）
- プロジェクト名: 例）`cursor_chat_history_exporter`（具体的なプロジェクト名）
- 目的/期間/主要ステークホルダー（任意）

## 実行手順（ローカル生成）
1. ディレクトリ作成（Stock直配置／プロジェクト基本構造＋実行フローフォルダ）
```bash
# 例: PROGRAM_ID=Tools PROJECT_ID=cursor_chat_history_exporter TODAY=$(date +%Y-%m-%d)
BASE="Stock/programs/$PROGRAM_ID/projects/$PROJECT_ID/documents"
# 基本フォルダ構造
mkdir -p "$BASE"/{1_initiating,2_discovery,2_research,3_planning,4_executing,5_monitoring,6_closing,9_event_preparation}
```
2. README/憲章ドラフト作成（最低限の雛形・Stock直配置）
```bash
cat > "Stock/programs/$PROGRAM_ID/projects/$PROJECT_ID/README.md" <<EOT
# $PROJECT_ID

## 概要
TBD

## 主要ステークホルダー
- TBD
EOT

cat > "$BASE/1_initiating/project_charter_$TODAY.md" <<EOT
# プロジェクト憲章（ドラフト）
- プログラム: $PROGRAM_ID
- プロジェクト: $PROJECT_ID
- 作成日: $TODAY

## 目的
TBD

## ステークホルダー
- TBD
EOT
```

## 次に実行
- 「01_憲章__プロジェクト憲章」でプロジェクト憲章を詳細化
- 「01_関係者__ステークホルダー分析」でステークホルダーを整理
- 「03_計画__WBS作成」で作業分解構造を作成

## 参照Rule
- `.cursor/rules/basic/00_master_rules.mdc`（プロジェクト初期化）
- `.cursor/rules/basic/01_pmbok_initiating.mdc`

## トラブルシュート
- 既存プロジェクトIDと重複する場合は上書きに注意（既存のREADMEを退避）
- Flow/Stockのルートに対する相対パスで実行してください
