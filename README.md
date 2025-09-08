# Cursor Chat History Exporter

Cursor のチャット履歴を安全・自動でエクスポートし、検索・再利用しやすい形で保存するツールです。

## なぜこのツールが必要？

### 課題
- **Cursor には公式のエクスポート API がない**: GUI での手動エクスポートは可能ですが、自動化や大量処理には向きません
- **履歴の散在**: 過去の重要な会話（設計判断、コード解説、学習内容）が埋もれてしまい、再利用が困難
- **監査・証跡の必要性**: 業務利用では、AI との会話履歴を体系的に保存・管理する必要がある場合があります
- **検索性の欠如**: 過去の会話から特定の情報を見つけるのに時間がかかります

### 解決策
このツールは Cursor のローカル SQLite データベース（`state.vscdb`）から直接チャット履歴を抽出し、以下を実現します：

- **自動化**: バッチ処理で大量の履歴を安全にエクスポート
- **構造化**: YAML 形式で機械可読・人間可読な形で保存
- **整理**: 日付別フォルダに自動整理、連続する同じ話者の発言を統合
- **再開性**: 処理が中断されても途中から再開可能
- **クロスプラットフォーム**: Windows/macOS/Linux で動作

## 主な特徴

- **安全な抽出**: Read-Only モードでデータベースにアクセス（Cursor を閉じる必要なし）
- **高品質な出力**: YAML Lint 準拠、文字化け対策、コード/マークダウンの保持
- **スマートな処理**: 空メッセージのスキップ、タイトル自動生成（先頭20文字）
- **バッチ処理**: 50件、100件などに分けて安全に処理
- **更新機能**: 特定の日付のデータだけを再生成可能

## インストール

### 必要な環境
- Python 3.9 以上
- Cursor を使用している環境

### セットアップ
```bash
# 1. このリポジトリをダウンロード/クローン
cd cursor_chat_history_exporter/Dev

# 2. 仮想環境を作成（推奨）
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. 依存関係をインストール
pip install pyyaml  # または requirements.txt があれば pip install -r requirements.txt
```

## 基本的な使い方

### 1. チャット履歴をエクスポート

```bash
cd Dev/src

# 全履歴を一括エクスポート（推奨）
python export_cursor_history.py --all --rescan

# または、段階的にエクスポート（大量データで安全に処理したい場合）
python export_cursor_history.py --batch-size 50 --rescan
python export_cursor_history.py --batch-size 100 --start-index 50
```

これで `@chat_history` フォルダに以下のような構造でファイルが作成されます：
```
@chat_history/
├── 2025-09-07_14-30-15_APIの使い方について_a1b2c3d4/
│   └── chat.yaml
├── 2025-09-07_15-45-22_Pythonのエラー解決_e5f6g7h8/
│   └── chat.yaml
└── export_manifest.json
```

### 2. 特定の日付のデータを更新

```bash
# 2025年9月7日のチャットデータだけを再生成
python update_standalone_chat_per_date.py --date 2025-09-07
```

これにより、指定日のデータが再生成されます。

### 3. エクスポートされたファイルを確認

各フォルダの `chat.yaml` ファイルには以下のような形式でチャット履歴が保存されます：

```yaml
---
threadId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
created_at: "2025-09-07_14-30-15"
title20: "APIの使い方について"
messages:
  - role: "user"
    content: |-
      FastAPIでREST APIを作る方法を教えてください。
      特にデータベース連携の部分が知りたいです。
  - role: "assistant"
    content: |-
      FastAPIでREST APIを作成する方法をご説明します。

      ## 基本的な構成
      ```python
      from fastapi import FastAPI
      app = FastAPI()
      ```
```

## 詳細オプション

### export_cursor_history.py のオプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--db` | Cursor データベースのパス | OS別自動検出 |
| `--out` | 出力先フォルダ | `@chat_history` |
| `--batch-size` | 一度に処理する件数 | 50 |
| `--start-index` | 開始インデックス | 0 |
| `--order` | 並び順（`desc`=新しい順, `asc`=古い順） | `desc` |
| `--rescan` | マニフェストを再生成 | - |
| `--all` | 全履歴を一括処理（batch-size無視） | - |

### update_standalone_chat_per_date.py のオプション

| オプション | 説明 | デフォルト |
|-----------|------|-----------|
| `--date` | 対象日（YYYY-MM-DD形式） | 必須 |
| `--db` | Cursor データベースのパス | OS別自動検出 |
| `--out` | 出力先フォルダ | `@chat_history` |

### データベースパスの自動検出

ツールは以下の場所からCursorのデータベースを自動検出します：

- **macOS**: `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`
- **Windows**: `%APPDATA%/Cursor/User/globalStorage/state.vscdb`
- **Linux**: `~/.config/Cursor/User/globalStorage/state.vscdb`

### カスタムパスの指定

```bash
# データベースパスを手動指定
python export_cursor_history.py --db "/path/to/your/state.vscdb"

# 出力先を変更
python export_cursor_history.py --out "my_chat_exports"
```

## よくある質問

### Q: Cursor を閉じる必要がありますか？
A: 通常は不要です。Read-Only モードでアクセスするため、Cursor を使いながらエクスポートできます。

### Q: "Untitled" のフォルダが作られません
A: 空のメッセージのみのスレッドは自動的にスキップされます。これは正常な動作です。

### Q: 大量の履歴がある場合はどうすれば？
A: 基本的には `--all` オプションで一括処理がおすすめです：
```bash
# 推奨：全履歴を一括処理
python export_cursor_history.py --all --rescan
```

より安全に段階的に処理したい場合は、バッチサイズを調整：
```bash
python export_cursor_history.py --batch-size 50 --rescan
python export_cursor_history.py --batch-size 100 --start-index 50
python export_cursor_history.py --batch-size 100 --start-index 150
```

### Q: エラーが発生した場合は？
A: マニフェストファイル（`export_manifest.json`）により、途中から再開できます。`--rescan` オプションで最初からやり直すことも可能です。

## トラブルシューティング

### データベースが見つからない
```bash
# パスを確認
ls ~/Library/Application\ Support/Cursor/User/globalStorage/state.vscdb  # macOS
# 手動でパスを指定
python export_cursor_history.py --db "/correct/path/to/state.vscdb"
```

### 権限エラー
```bash
# 読み取り権限を確認
ls -la ~/Library/Application\ Support/Cursor/User/globalStorage/state.vscdb
```

## ライセンス

このツールは一般公開を想定して作成されています。機密情報を含むチャット履歴の取り扱いについては、各組織のポリシーに従ってください。

---

## Appendix: AIPM システム利用者向け

AIPM（AI Project Management）システムを使用している場合、エクスポートしたデータを Flow フォルダ構造に統合できます。

### 追加スクリプト
- `move_and_organize_chats.py`: `@chat_history` から `Flow/YYYYMM/YYYY-MM-DD/chats/` に移動
- `update_latest_chat_per_date.py`: Flow 内の特定日データを再生成し `latest_chat.yaml` を作成
- `update_latest_chats_for_dates.py`: 複数日を一括再生成

### AIPM 向け使用例

```bash
# 1. 通常通りエクスポート
python export_cursor_history.py --batch-size 50 --rescan

# 2. Flow フォルダに移動・整理
python move_and_organize_chats.py --src "@chat_history" --flow "../../../../../Flow"

# 3. 特定日の Flow データを再生成
python update_latest_chat_per_date.py --date 2025-09-07 --flow "../../../../../Flow"

# 4. 複数日を一括再生成
python update_latest_chats_for_dates.py --dates 2025-09-07 2025-09-06 --flow "../../../../../Flow"
```

### Flow 構造での出力
```
Flow/
├── 202509/
│   └── 2025-09-07/
│       └── chats/
│           ├── 2025-09-07_14-30-15_APIの使い方について_a1b2c3d4/
│           └── 2025-09-07_15-45-22_Pythonのエラー解決_e5f6g7h8/
```

AIPM システムの詳細については、システム管理者にお問い合わせください。

## 免責・注意事項
- 本ツールは非公式です。Cursorやサードパーティの互換性変更により動作が変わる可能性があります。
- 出力される `chat.yaml` には機密情報（個人情報・アクセスキー・社外秘情報）が含まれる場合があります。公開リポジトリや共有ドライブにアップロードする前に必ず内容を確認し、必要に応じてマスキング・除去を行ってください。
- 出力フォルダの誤指定・誤削除により過去のエクスポート成果物が失われる恐れがあります。重要な成果物は別途バックアップしてください。
- スクリプトは読み取り専用でDBを開く設計ですが、OSや環境差異によりロック・一時ファイル生成等の挙動が異なることがあります。長時間の実行や大量エクスポート時は十分な空き容量を確保してください。
- エクスポート結果をFlow等へ移動するスクリプトはファイルの移動・削除を行います。実行前にパスと対象を必ず確認し、テスト用ディレクトリで動作検証してから本運用へ適用してください。
- 利用に伴ういかなる損害についても、作者・提供者は一切の責任を負いません。自己責任でご利用ください。

## Commands（Cursor コマンド連携）

本ツールは Cursor の Commands 機能と連携して、日次同期をノーコードで実行できます。

### 配置場所
- Dev 直下に `.cursor/commands/chat-history-update.md` を同梱しています（config は空欄）
- AIPM ワークスペース標準の場所は `/.cursor/commands/general/chat-history-update.md` です

### 初期設定（はじめて使う場合）
1. `.cursor/commands/chat-history-update.md` を AIPM ルート配下の `/.cursor/commands/` にコピー
2. 開いたファイルの `config` セクションを環境に合わせて設定（空欄のままでも Preflight が自動検出可能）
   - `workspace`: ワークスペースの絶対パス（例: `/Users/you/your_repo`）
   - `repo_rel`: 本ツールの `Dev/src` への相対パス（例: `Stock/programs/Tools/projects/cursor_chat_history_exporter/Dev/src`）
   - `flow_rel`: Flow ルート相対パス（例: `Flow`）
   - `out_rel`: スタンドアロン出力先（例: `@chat_history`）
   - `db_path`: Cursor の DB パス（未設定可。OS別既定: `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` 等）

### 使い方（Commands 実行）
- コマンド名: 「チャット履歴更新（Flow自動同期）」
- 推奨手順:
  1) Preflight を実行（config 未設定時の自動検出＆検証）
  2) quick_run を実行（昨日分の再生成＋直近7日の不足分補完）
  3) 必要に応じて「昨日のみ」「本日」「指定日」「直近N日」「日付範囲」を実行

### 備考
- config が空欄でも quick_run は自動検出で動作可能
- macOS の `date -v` 使用（Linux は `date -d` へ読み替え）
- 生成先（AIPM モード）: `Flow/YYYYMM/YYYY-MM-DD/chats/`
- 生成先（スタンドアロン）: `@chat_history/YYYY-MM-DD_/...`
