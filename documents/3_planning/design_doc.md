# cursor_chat_history_exporter - Design Doc（設計文書）

**作成者:** Tools Program Team  
**作成日:** 2025-09-07  
**ステータス:** 最終版  
**バージョン:** 1.0

## 1. コンテキストとスコープ

### 問題の説明
Cursor のローカルDB（`state.vscdb`）からチャット履歴を安定抽出し、YAMLで保存・日付整理・最新反映まで自動化する。大量履歴向けに再開性（manifest）と日付単位の再生成を提供する。

### 背景
公式APIがなく、GUIエクスポートは再現性や完全性に課題。監査、検索、ナレッジ再利用のため、機械可読・人間可読の両立が必要。

## 2. 目標と非目標

### 目標
- DBをRead-Onlyで安全参照し、スレッド→バブルを抽出
- 連続同一ロール連結、空メッセージ除外、YAML整形（Lint準拠）
- `Flow/YYYYMM/YYYY-MM-DD/chats/` への配置と `latest_chat.yaml` 作成
- 指定日・複数日の完全再生成

### 非目標
- クラウド同期UI、全文検索SaaS、可視化ダッシュボード

## 3. 設計概要
シンプルなスクリプト群で疎結合に構成。抽出（Export）と配置（Move/Organize）と再生成（Update）を分離し、失敗時の再実行が容易。DB参照は `file:...mode=ro`。フォルダ名はタイトルor先頭20文字スラグを採用。

## 4. 詳細設計

### 技術的アプローチ
- 言語: Python 3
- DB: SQLite（Read-Only URI）
- 構成:
  - `export_cursor_history.py`: 抽出・整形・YAML書出し・manifest管理
  - `move_and_organize_chats.py`: `@chat_history` → `Flow/.../chats/` 移動集約
  - `update_latest_chat_per_date.py`: 指定日再生成（chatsクリア→再抽出→最新作成）
  - `update_latest_chats_for_dates.py`: 複数日一括

### データモデル/ストレージ
- 入力: `cursorDiskKV` の `composerData:*`（スレッド）, `bubbleId:<cid>:*`（メッセージ）
- 出力: `chat.yaml`（block scalar、サニタイズ済み）、`latest_chat.yaml`
- 補助: `export_manifest.json`（進捗/再開）

### API/インターフェース
CLI引数のみ（対象件数、日付、出力ディレクトリ）。DBパスは既定値（Cursor標準）または上書き可能。

### スケーラビリティとパフォーマンス
- バッチ処理（例: 50/100件）とスリープで負荷平準化
- 再開（manifest）で長時間バッチの中断耐性

## 5. 代替案とトレードオフ
- 代替: GUI手動エクスポート → 再現性/自動化に難
- 代替: 外部SaaS（Opik/Langfuse等） → データ持ち出し懸念、依存増
- 現行はローカル完結・軽量、UIなしだが運用容易

## 6. 懸念事項と考慮点
- セキュリティ: ローカルDB参照限定。成果物は社内保存/権限管理
- プライバシー: 機微情報の含有に留意。必要に応じマスキング拡張
- テクニカルデット: DB内部キーの将来変更リスク→キー探索の冗長化で軽減

## 7. 実装とテスト計画
- 単体テスト: 小規模DBでの件数別/日付別抽出検証
- 回帰: YAML Lint、文字化け・ゼロ幅除去確認
- 運用テスト: 複数日の再生成と再実行耐性

## 付録（関連）
- `documents/1_initiating/project_charter.md`
- `documents/2_discovery/problem_statement.md`
- `documents/2_discovery/solution_definition.md`

