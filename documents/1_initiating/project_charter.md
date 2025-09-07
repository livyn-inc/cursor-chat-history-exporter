# プロジェクト憲章（確定）

- プログラム: Tools
- プロジェクト: cursor_chat_history_exporter
- バージョン: v1.0
- 作成日: 2025-09-07

## 1. 背景 / ビジネスケース
Cursor には公式のCLI/APIによるチャット履歴エクスポートが存在せず、履歴の保存・検索・再利用が難しい。業務知見の蓄積、監査・証跡、横断検索、学習データ整備の観点から、安定的かつ再現性のあるローカルエクスポート手段が必要。

## 2. 目的 / 目標
- Cursor のローカルDB（state.vscdb）からチャットを抽出し、YAMLで保存する。
- 生成物を `Flow/YYYYMM/YYYY-MM-DD/chats/` に整然と配置し、同日に `latest_chat.yaml` を用意する。
- バッチ・再開対応とし、大量履歴でも安全に処理できる。
- 指定日を再構築（chats 全消去 → DB再抽出 → 最新反映）できるメンテナンス機能を備える。

### 成果指標（Success Criteria）
- 1000件超の履歴をエラーなくYAML化し、Lintエラー0。
- 指定日の `latest_chat.yaml` が常に最新スレッドを指す。
- 連続同一ロールの結合・空メッセージ除去・コード/Markdown保持（フェンス）を満たす。

## 3. スコープ
### 含む
- ローカルDB読取とYAML出力（グルーピング/スピーカ付与/サニタイズ）。
- `@chat_history` → Flow への移動と日付配下 `chats/` への集約。
- 指定日/複数日再生成ツール。

### 含まない
- クラウド同期、全文検索UI、タグ付けUI、外部SaaS連携。

## 4. 主要成果物
- Devスクリプト一式（GitHub公開想定）
  - `export_cursor_history.py`（バッチ・再開）
  - `move_and_organize_chats.py`（移動＋集約）
  - `update_latest_chat_per_date.py`（日付再生成）
  - `update_latest_chats_for_dates.py`（複数日再生成）
- Flow 配下の `chats/` フォルダ構造と `latest_chat.yaml`
- Dev/README（運用手順）

## 5. 利害関係者 / 体制
- プロジェクトオーナー: Requester（本ワークスペースの利用者）
- 開発/運用: Tools プログラム内チーム
- レビュワー: ドキュメント利用者（業務・監査担当）

## 6. マイルストーン
- M1: エクスポータ実装（YAML / グルーピング / サニタイズ）
- M2: Flow 連携（移動・集約）
- M3: 再生成ワークフロー（日付・複数日）
- M4: ドキュメント整備・公開（README / ひな形）

## 7. リスクと対策
- DB仕様変更で抽出失敗 → read-only URI・キー探索ロジックの冗長化、バグ時はマニフェスト再走査。
- 大量処理でのエラー → バッチ化・再開点記録（manifest）・スリープ挿入。
- YAML Lint 不整合 → block scalar・ゼロ幅/BOM除去・タブ→スペースの一括処理。

## 8. 承認
- 本ドキュメントの内容をもって、`cursor_chat_history_exporter` を正式なツールプロジェクトとして開始する。
