# ソリューション定義：cursor_chat_history_exporter

## 1. 課題仮説

### 背景
Cursor はローカルDB（`state.vscdb`）にチャット履歴を保持するが、公式のCLI/APIがないため、自動エクスポート・日次整理・再生成が難しい。GUIの手動エクスポートは情報欠落や再現性の問題があり、監査・検索・ナレッジ再利用が非効率。

### 課題/ニーズ
履歴を安全・再現可能にエクスポートし、機械可読（YAML）かつ人間が読みやすい形で日付フォルダへ自動整理したい。大量履歴に対してバッチ・再開が可能で、指定日を完全再生成できるメンテナンス性が必要。

## 2. ソリューション仮説
ローカルDBを読み取り専用で参照し、スレッド→メッセージ抽出→ロール付与→同一ロール連結→空メッセージ除外→YAML整形（Lint準拠）→Flow配下へ日付整理→`latest_chat.yaml`作成までを一連のスクリプトで自動化することで、履歴の保存・再利用効率が大幅に向上する。

## 3. ソリューションの主要機能
- エクスポート: `export_cursor_history.py`
  - `cursorDiskKV` の `composerData:*` と `bubbleId:*` を対象に、スレッドとバブルを抽出
  - ロール推定（type/role/authorRole/sender）と連続同一ロール連結、空メッセージ除外
  - タイトル未設定時は先頭20文字からフォルダ名生成、YAML出力、manifestで再開可能
- 移動・集約: `move_and_organize_chats.py`
  - `@chat_history` → `Flow/YYYYMM/YYYY-MM-DD/chats/` へ移動
- 日付再生成: `update_latest_chat_per_date.py`
  - 指定日の `chats/` をクリア→DB再抽出→再生成→`latest_chat.yaml` 更新
- 複数日再生成: `update_latest_chats_for_dates.py`
  - 日付リストをループして上記再生成を一括実行

## 4. 仕様詳細
- DB接続: SQLite Read-Only URI（`file:...state.vscdb?mode=ro`）
- 抽出キー: `composerData:<UUID>`（スレッド）、`bubbleId:<composerId>:<UUID>`（メッセージ）
- 日付変換: epoch(ms) → ローカルタイム
- YAML整形: block scalar、BOM/ゼロ幅除去、タブ→スペース、行末正規化
- スキップ条件: 全メッセージ空（Untitled）スレッドは出力しない
- 出力: `Flow/YYYYMM/YYYY-MM-DD/chats/<title20>_<created>*/chat.yaml`

## 5. 関連リソース
- Dev/README に手順とコマンド例を記載
- スクリプト群: `Stock/programs/Tools/projects/cursor_chat_history_exporter/Dev/src`

## 6. 次のステップ
1. 週次での自動実行ジョブ（crontab/launchd）雛形追加
2. 失敗時リトライとサマリーレポート（処理件数/スキップ件数）出力
3. タグ/検索メタ（モデル種別、拡張機能名）付与の拡張検討

