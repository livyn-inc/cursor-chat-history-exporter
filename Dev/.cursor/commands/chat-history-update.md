name: "チャット履歴更新（Flow自動同期）"
description: |
  Cursorのチャット履歴をDBから抽出し、Flow/YYYYMM/YYYY-MM-DD/chats/ へ日次同期します。
  昨日分のchatsフォルダが見つからない場合は、直近数日を自動で探索して不足分のみ更新します。

ai_instructions:
  - "各ステップを正確に実行すること。独自処理は追加しないこと"
  - "対話不要。非インタラクティブに完了させること"
  - "macOS想定のdateコマンド（-vオプション）を使用。Linuxの場合は適宜置換可"

# 環境設定（外部公開用に編集可能な変数）
config:
  # ワークスペースの絶対パス（空欄の場合はPreflightで自動検出）
  workspace: ""
  # Example: "/Users/username/project_directory"

  # 相対パス（workspace からの相対、空欄の場合はPreflightで自動検出）
  repo_rel: ""
  # Example: "cursor-chat-history-exporter/Dev/src"
  
  flow_rel: ""
  # Example: "Flow"
  
  out_rel: ""
  # Example: "@chat_history"

  # CursorのローカルDBパス（ユーザーHOMEに依存）
  db_path: ""

# ワンコマンド実行（昨日分は常に再生成＋直近7日は不足のみ補完）
quick_run:
  command: "if [ -z \"{{config.workspace}}\" ] || [ -z \"{{config.repo_rel}}\" ] || [ -z \"{{config.flow_rel}}\" ] || [ -z \"{{config.out_rel}}\" ]; then echo \"[quick_run] ⚠️  config設定が空欄です。Preflightを先に実行してください\"; echo \"[quick_run] 🔧 自動検出を開始します...\"; CURRENT_WS=\"$(pwd)\"; if [ -d \"$CURRENT_WS/cursor-chat-history-exporter/Dev/src\" ]; then WS=\"$CURRENT_WS\"; REPO=\"$WS/cursor-chat-history-exporter/Dev/src\"; FLOW=\"$WS/Flow\"; OUT=\"$WS/@chat_history\"; else echo \"[quick_run] ❌ cursor-chat-history-exporterが見つかりません\"; exit 1; fi; else WS=\"{{config.workspace}}\"; REPO=\"$WS/{{config.repo_rel}}\"; FLOW=\"$WS/{{config.flow_rel}}\"; OUT=\"$WS/{{config.out_rel}}\"; fi; DB=\"{{config.db_path}}\"; echo \"[quick_run] Preflight...\"; if [ ! -d \"$WS\" ] || [ ! -d \"$REPO\" ] || [ ! -d \"$FLOW\" ]; then echo \"ERROR: 環境設定を確認してください (workspace/repo_rel/flow_rel)\"; exit 1; fi; if [ ! -f \"$REPO/update_latest_chat_per_date.py\" ]; then echo \"ERROR: スクリプトが見つかりません: update_latest_chat_per_date.py\"; exit 1; fi; mkdir -p \"$OUT\"; YESTERDAY=$(date -v-1d +%Y-%m-%d); python3 \"$REPO/update_latest_chat_per_date.py\" --date \"$YESTERDAY\" --db \"$DB\" --flow \"$FLOW\"; for i in 2 3 4 5 6 7; do D=$(date -v-${i}d +%Y-%m-%d); YM=${D:0:4}${D:5:2}; DIR=\"$FLOW/$YM/$D/chats\"; if [ ! -d \"$DIR\" ] || [ -z \"$(ls -A \"$DIR\" 2>/dev/null)\" ]; then python3 \"$REPO/update_latest_chat_per_date.py\" --date \"$D\" --db \"$DB\" --flow \"$FLOW\"; fi; done"
  message: "🗂 昨日分は常に再生成し、直近7日は未生成日のみ補完します（config空欄時は自動検出）"
  instruction: "このコマンドのみを実行（config設定が空欄でも動作します）"

# 補助フロー（必要に応じて個別実行）
flows:
  preflight:
    description: "config設定が空欄の場合に実行: 環境設定と依存関係の自動検出・設定"
    steps:
      - name: "check_config_and_auto_detect"
        action: "execute_shell"
        command: "echo \"[Preflight] config設定をチェック中...\"; if [ -n \"{{config.workspace}}\" ] && [ -n \"{{config.repo_rel}}\" ] && [ -n \"{{config.flow_rel}}\" ] && [ -n \"{{config.out_rel}}\" ]; then echo \"[Preflight] ✅ config設定が完了しています。環境チェックのみ実行します\"; WS=\"{{config.workspace}}\"; REPO=\"$WS/{{config.repo_rel}}\"; FLOW=\"$WS/{{config.flow_rel}}\"; OUT=\"$WS/{{config.out_rel}}\"; else echo \"[Preflight] 🔧 config設定が空欄です。自動検出を開始します...\"; CURRENT_WS=\"$(pwd)\"; echo \"[Preflight] 現在のワークスペース: $CURRENT_WS\"; if [ -d \"$CURRENT_WS/cursor-chat-history-exporter/Dev/src\" ]; then DETECTED_REPO=\"cursor-chat-history-exporter/Dev/src\"; echo \"[Preflight] ✅ cursor-chat-history-exporter を検出: $DETECTED_REPO\"; WS=\"$CURRENT_WS\"; REPO=\"$WS/$DETECTED_REPO\"; FLOW=\"$WS/Flow\"; OUT=\"$WS/@chat_history\"; else echo \"[Preflight] ❌ cursor-chat-history-exporter が見つかりません\"; exit 1; fi; if [ ! -d \"$FLOW\" ]; then echo \"[Preflight] 🔧 Flow ディレクトリを作成中...\"; mkdir -p \"$FLOW\"; echo \"[Preflight] ✅ Flow ディレクトリを作成しました\"; fi; if [ ! -d \"$OUT\" ]; then echo \"[Preflight] 🔧 @chat_history ディレクトリを作成中...\"; mkdir -p \"$OUT\"; echo \"[Preflight] ✅ @chat_history ディレクトリを作成しました\"; fi; echo \"[Preflight] 🔧 Commands ファイルの config を自動更新中...\"; COMMANDS_FILE=\"$CURRENT_WS/.cursor/commands/chat-history-update.md\"; if [ -f \"$COMMANDS_FILE\" ]; then echo \"[Preflight] 更新前のconfig:\"; grep -A 10 \"workspace:\" \"$COMMANDS_FILE\" | head -8; sed -i '' \"s|^  workspace: \\\"\\\\\\\\\\\\\\\"$|  workspace: \\\"$CURRENT_WS\\\"|g\" \"$COMMANDS_FILE\"; sed -i '' \"s|^  repo_rel: \\\"\\\\\\\\\\\\\\\"$|  repo_rel: \\\"$DETECTED_REPO\\\"|g\" \"$COMMANDS_FILE\"; sed -i '' \"s|^  flow_rel: \\\"\\\\\\\\\\\\\\\"$|  flow_rel: \\\"Flow\\\"|g\" \"$COMMANDS_FILE\"; sed -i '' \"s|^  out_rel: \\\"\\\\\\\\\\\\\\\"$|  out_rel: \\\"@chat_history\\\"|g\" \"$COMMANDS_FILE\"; echo \"[Preflight] 更新後のconfig:\"; grep -A 10 \"workspace:\" \"$COMMANDS_FILE\" | head -8; echo \"[Preflight] ✅ Commands ファイルを自動更新しました\"; echo \"[Preflight] 📄 更新されたファイル: $COMMANDS_FILE\"; else echo \"[Preflight] ⚠️  Commands ファイルが見つかりません: $COMMANDS_FILE\"; fi; fi"
        message: "config設定をチェックし、空欄の場合は自動検出してCommandsファイルのconfigを実際に更新"
      - name: "check_paths_and_tools"
        action: "execute_shell"
        command: "WS=\"{{config.workspace}}\"; REPO=\"$WS/{{config.repo_rel}}\"; FLOW=\"$WS/{{config.flow_rel}}\"; OUT=\"$WS/{{config.out_rel}}\"; DB=\"{{config.db_path}}\"; echo \"[Preflight] workspace=$WS\"; if [ ! -d \"$WS\" ]; then echo \"ERROR: workspace が存在しません: $WS\"; exit 1; fi; echo \"[Preflight] repo=$REPO\"; if [ ! -d \"$REPO\" ]; then echo \"ERROR: REPO ディレクトリが見つかりません: $REPO\"; exit 1; fi; if [ ! -f \"$REPO/update_latest_chat_per_date.py\" ]; then echo \"ERROR: スクリプトが見つかりません: update_latest_chat_per_date.py\"; exit 1; fi; if [ ! -f \"$REPO/update_standalone_chat_per_date.py\" ]; then echo \"ERROR: スクリプトが見つかりません: update_standalone_chat_per_date.py\"; exit 1; fi; echo \"[Preflight] flow=$FLOW\"; if [ ! -d \"$FLOW\" ]; then echo \"ERROR: Flow ディレクトリが存在しません: $FLOW\"; exit 1; fi; echo \"[Preflight] out=$OUT\"; if [ ! -d \"$OUT\" ]; then echo \"[Preflight] OUTが無いので作成します: $OUT\"; mkdir -p \"$OUT\"; fi; echo \"[Preflight] db=$DB\"; if [ ! -f \"$DB\" ]; then echo \"WARNING: DB ファイルが見つかりません: $DB\"; fi; which python3 >/dev/null 2>&1 || { echo \"ERROR: python3 が見つかりません\"; exit 1; }; python3 --version; date -v-1d +%Y-%m-%d >/dev/null 2>&1 || echo \"NOTE: macOSのdate -vが未対応（Linuxは 'date -d' を使用してください）\"; echo \"[Preflight] ✅ 全ての環境チェックが完了しました\""
        message: "環境チェックを実行します（WS/REPO/FLOW/OUT/DB/Python/date）"
  update_yesterday_only:
    description: "昨日のchatsのみ再生成（存在しても上書き）"
    steps:
      - name: "rebuild_yesterday"
        action: "execute_shell"
        command: "WS=\"{{config.workspace}}\"; REPO=\"$WS/{{config.repo_rel}}\"; FLOW=\"$WS/{{config.flow_rel}}\"; DB=\"{{config.db_path}}\"; D=$(date -v-1d +%Y-%m-%d); python3 \"$REPO/update_latest_chat_per_date.py\" --date \"$D\" --db \"$DB\" --flow \"$FLOW\""
        message: "昨日のFlow/chatsを再生成しています"

  backfill_recent_7days:
    description: "直近7日分で未生成・空のchatsのみを補完生成"
    steps:
      - name: "backfill_missing"
        action: "execute_shell"
        command: "WS=\"{{config.workspace}}\"; REPO=\"$WS/{{config.repo_rel}}\"; FLOW=\"$WS/{{config.flow_rel}}\"; DB=\"{{config.db_path}}\"; for i in 1 2 3 4 5 6 7; do D=$(date -v-${i}d +%Y-%m-%d); YM=${D:0:4}${D:5:2}; DIR=\"$FLOW/$YM/$D/chats\"; if [ ! -d \"$DIR\" ] || [ -z \"$(ls -A \"$DIR\" 2>/dev/null)\" ]; then python3 \"$REPO/update_latest_chat_per_date.py\" --date \"$D\" --db \"$DB\" --flow \"$FLOW\"; fi; done"
        message: "未生成日のみを対象に直近7日を補完"

  update_specific_date:
    description: "指定日のFlow/chatsを完全再生成（中身をクリアしてから再出力）"
    steps:
      - name: "rebuild_specific_date"
        action: "execute_shell"
        command: "WS=\"{{config.workspace}}\"; REPO=\"$WS/{{config.repo_rel}}\"; FLOW=\"$WS/{{config.flow_rel}}\"; DB=\"{{config.db_path}}\"; TARGET=\"{{target_date}}\"; python3 \"$REPO/update_latest_chat_per_date.py\" --date \"$TARGET\" --db \"$DB\" --flow \"$FLOW\""
        message: "指定日のFlow/chatsを再生成します（例: target_date=2025-09-07）"

  standalone_update_specific_date:
    description: "Non-AIPM向け：@chat_history配下で指定日のみ更新（Flowを使わない）"
    steps:
      - name: "standalone_rebuild"
        action: "execute_shell"
        command: "WS=\"{{config.workspace}}\"; REPO=\"$WS/{{config.repo_rel}}\"; DB=\"{{config.db_path}}\"; TARGET=\"{{target_date}}\"; OUT=\"$WS/{{config.out_rel}}\"; python3 \"$REPO/update_standalone_chat_per_date.py\" --date \"$TARGET\" --db \"$DB\" --out \"$OUT\""
        message: "指定日を@chat_historyに再生成します（Flowを使わない運用向け）"

  update_today_only:
    description: "今日のFlow/chatsを完全再生成（存在しても上書き）"
    steps:
      - name: "rebuild_today"
        action: "execute_shell"
        command: "WS=\"{{config.workspace}}\"; REPO=\"$WS/{{config.repo_rel}}\"; FLOW=\"$WS/{{config.flow_rel}}\"; DB=\"{{config.db_path}}\"; D=$(date +%Y-%m-%d); python3 \"$REPO/update_latest_chat_per_date.py\" --date \"$D\" --db \"$DB\" --flow \"$FLOW\""
        message: "今日のFlow/chatsを再生成しています"

  force_recent_ndays:
    description: "直近N日を強制再生成（今日含む）"
    params:
      - key: "days"
        required: true
        note: "例: 7（今日から7日分）"
    steps:
      - name: "force_rebuild_recent_ndays"
        action: "execute_shell"
        command: "WS=\"{{config.workspace}}\"; REPO=\"$WS/{{config.repo_rel}}\"; FLOW=\"$WS/{{config.flow_rel}}\"; DB=\"{{config.db_path}}\"; N=\"{{days}}\"; i=0; while [ \"$i\" -lt \"$N\" ]; do D=$(date -v-${i}d +%Y-%m-%d); python3 \"$REPO/update_latest_chat_per_date.py\" --date \"$D\" --db \"$DB\" --flow \"$FLOW\"; i=$((i+1)); done"
        message: "直近N日を強制再生成します（N={{days}}）"

  force_date_range:
    description: "指定した日付範囲を強制再生成（開始日〜終了日、両端含む）"
    params:
      - key: "start_date"
        required: true
        note: "形式: YYYY-MM-DD"
      - key: "end_date"
        required: true
        note: "形式: YYYY-MM-DD"
    steps:
      - name: "force_rebuild_range"
        action: "execute_shell"
        command: "WS=\"{{config.workspace}}\"; REPO=\"$WS/{{config.repo_rel}}\"; FLOW=\"$WS/{{config.flow_rel}}\"; DB=\"{{config.db_path}}\"; START=\"{{start_date}}\"; END=\"{{end_date}}\"; D=\"$START\"; while :; do python3 \"$REPO/update_latest_chat_per_date.py\" --date \"$D\" --db \"$DB\" --flow \"$FLOW\"; if [ \"$D\" = \"$END\" ]; then break; fi; D=$(date -j -f %Y-%m-%d \"$D\" -v+1d +%Y-%m-%d); done"
        message: "指定期間（{{start_date}}〜{{end_date}}）を強制再生成します"

outputs:
  - "{{config.workspace}}/Flow/YYYYMM/YYYY-MM-DD/chats/ (または自動検出されたワークスペース)"
  - "{{config.workspace}}/@chat_history/YYYY-MM-DD/ (standalone時、または自動検出されたワークスペース)"

notes:
  - "DBは read-only で参照。スクリプトは YAML（chat.yaml）を生成し、空メッセージはスキップ、役割でグルーピング済み"
  - "macOSのdate -v を使用。Linuxの場合は date -d \"-1 day\" 等に置換してください"
  - "大量更新が必要な場合は、別途 export_cursor_history.py --all と move_and_organize_chats.py の併用も可能"
  - "🆕 Preflightでconfig自動更新: 空欄のconfig設定を自動検出した値で実際に更新し、以降は手動設定として動作"
  - "🚀 quick_runは config設定が空欄でも動作: 空欄の場合は自動的に現在のワークスペースを検出して実行"
  - "✅ 初回利用時: config設定を空欄のままPreflightを実行 → 自動検出してconfig更新 → 以降は更新された設定で動作"
  - "🔧 手動設定も可能: config設定に具体的な値を入力すれば、その設定を優先して使用"
  - "📄 設定の永続化: Preflightで一度更新されたconfig設定は、Commandsファイルに保存され、次回以降も使用される"
  - "Linux環境では 'date -v' が使えないため、'date -d' 形式に置換してください（例：$(date -d '-1 day' +%Y-%m-%d)）"
