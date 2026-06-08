# UTAGE AI Skill - messages

メール・LINE・SMS・アクション配信の作成・編集・削除を行います。特にステップ配信、一斉配信、リマインダー配信で使います。

## MCPツール

> `message_*` は現行MCPではプレビュー扱いです。作業前に `find_tools(category="message")` で最新の引数・注意書きを確認してください。

| ツール名 | 操作 |
|:---|:---|
| `message_list` | メッセージ一覧取得 |
| `message_get` | メッセージ詳細取得 |
| `message_create` | メッセージ作成 |
| `message_update` | メッセージ更新（PUT: 全フィールド必須） |
| `message_delete` | メッセージ削除 |
| `message_test_send` | テスト送信 |
| `message_stats_get` | 配信統計取得 |
| `message_action_list` | アクション一覧取得（作成は不可） |
| `message_tracking_list` / `message_tracking_stats` | 登録経路・トラッキング取得 |
| `message_label_list` / `message_label_create` / `message_label_get` | ラベル取得・作成 |
| `message_label_update` / `message_label_delete` | ラベル更新・削除 |
| `message_common_reader_label_list` / `message_common_reader_label_create` / `message_common_reader_label_delete` | 読者へのラベル付与・削除 |
| `message_reader_list_all` / `message_reader_list` / `message_reader_get` | 読者データ参照 |
| `message_placeholder_list` | 置き換え文字・読者項目一覧取得 |
| `message_condition_types` | 配信条件・読者絞り込み条件の定義取得 |
| `message_types_line` | LINEメッセージタイプ定義取得 |
| `message_line_sender_list` / `message_line_sender_get` / `message_line_sender_create` | LINEカスタム送信者取得・作成 |
| `message_line_sender_update` / `message_line_sender_delete` | LINEカスタム送信者更新・削除 |
| `element_types_mail` / `element_types_mail_properties` | HTMLメール要素タイプ定義取得 |

---

## ⚠️ 注意点

> → 全カテゴリ共通トラップはルートの SKILL.md を参照

### メッセージ固有の注意

- **`send_type` は必須**。省略すると `validation_error`。値は `"scheduled"` or `"immediately"`
- **即時ステップの安全制限**。`send_type: "immediately"` 自体は使えるが、`step_send_type: "immediately"` のまま `reserved` へ戻すと `safety_restriction` になる場合がある。既存値を確認し、必要なら `step_send_type: "none"` で復旧する
- **PUT は全フィールド必須**。未指定フィールドは null にリセットされる。必ず `message_get` で現在値を取得してから、変更箇所だけ書き換えて送信すること
- **予約済みメッセージは直接編集できない**。`status=reserved` の本文・件名・条件等を変える場合は、まず `status: "draft"` にするPUTを送り、再取得してから変更済み全量payloadで `status: "reserved"` に戻す
- **`message_update` のキー省略不可**。`title`, `use_ab_test`, `action_id`, `shorten_domain`, `shorten_type`, `conditions`, `url_actions`, および該当チャンネルの `mail` / `line` / `sms` は null や空配列でもキーを含める
- **`channel` / `type` は作成後変更不可**。既存 `message_get` の値を維持する
- **メール本文には配信解除URL（`%cancel%` or `%cancelall%`）を必ず含める**こと。含めないとバリデーションエラー
- **件名ABテスト**は `use_ab_test: 1` と `mail.subject_pattern_b` をセットで送る
- **HTMLメールのelementsはフラット構造**。`element_types_mail_properties` の `properties` は定義一覧であり、作成データを `properties: {...}` で包まない
- **読者絞り込み条件は推測しない**。`message_condition_types` と `message_placeholder_list` の `is_filterable=true` を確認してから使う
- **アクション配信**（`channel: "action"`）は `message_action_list` で取得した `action_id` を使う。アクション自体の作成は管理画面のみ
- **LINE送信者更新はPUTセマンティクス**。`message_line_sender_get` で現在値を取得し、`name` と `image_url` の両方を送る
- **LINE送信者の作成・削除は本番表示に影響する**。`message_line_sender_create` / `message_line_sender_delete` は事前確認を取る
- **テスト送信**は `message_test_send` を使う。`step` / `reminder` でも即時送信されるため、本番読者宛では使わない

---

## メッセージ作成の必須パラメータ

### ステップメール（channel: mail）

```json
{
  "account_id": "...",
  "scenario_id": "...",
  "channel": "mail",
  "type": "step",
  "send_type": "scheduled",
  "send_date": 2,
  "send_hour": 18,
  "send_min": 0,
  "title": "管理名",
  "mail": {
    "type": "plain_text",
    "from_mail": "info@example.com",
    "from_name": "送信者名",
    "subject": "件名",
    "text": "本文\n\n配信解除: %cancel%"
  }
}
```

### LINE配信（channel: line）

```json
{
  "account_id": "...",
  "scenario_id": "...",
  "channel": "line",
  "type": "step",
  "send_type": "scheduled",
  "send_date": 1,
  "send_hour": 18,
  "send_min": 0,
  "title": "LINE 2通目",
  "line": {
    "messages": [
      {
        "type": "text",
        "text": "メッセージ本文"
      }
    ]
  }
}
```

### send_type の値

| 値 | 意味 | 追加パラメータ |
|:---|:---|:---|
| `"immediately"` | 登録直後に送信 | 不要（send_date等は無視） |
| `"scheduled"` | 指定日時に送信 | `send_date`（日数）+ `send_hour` + `send_min` |
| `"scheduled_addition"` | 追加配信 | 追加配信用の日時・条件 |

### message_update の安全な更新手順

1. `message_get(account_id, scenario_id, message_id)` で現在値を取得
2. 予約済みなら、現在値をもとに `status: "draft"` だけ変えた全量payloadを `message_update` に送る
3. 再度 `message_get` でdraft状態の現在値を取得
4. 変更箇所を反映し、必須キーをすべて含めて `message_update`
5. 稼働させる場合は `status: "reserved"` に戻し、最後に `message_get` で確認

最低限維持するトップレベルキー。実際の更新では、`message_get` で得た `mail` / `line` / `sms` の中身も省略せず保持します。

```json
{
  "title": "...",
  "use_ab_test": 0,
  "action_id": null,
  "shorten_domain": null,
  "shorten_type": "shorten_url",
  "conditions": [],
  "url_actions": [],
  "mail": {}
}
```

LINEなら `mail` ではなく `line`、SMSなら `sms` を含める。即時ステップで `safety_restriction` が出る場合は、`send_type: "immediately"` は維持しつつ `step_send_type: "none"` を試す。

### HTMLメール elements の形

`element_types_mail_properties` の `properties` は「使えるプロパティ一覧」です。実データでは `properties` キーで包まず、要素オブジェクトに直接展開します。

```json
{
  "type": "section",
  "background_color": "#ffffff",
  "children": [
    {
      "type": "row",
      "children": [
        {
          "type": "col",
          "children": [
            {"type": "text", "content": "<p>本文</p>"}
          ]
        }
      ]
    }
  ]
}
```

### テスト送信

2026-05-16 実操作確認:

```json
{
  "tool": "message_test_send",
  "to": "icloudaichi@gmail.com",
  "from_mail": "info@hirahara-daichi.com",
  "result": {"success": true}
}
```

テスト送信用のメッセージも、メール本文に `%cancel%` または `%cancelall%` が必要です。

---

## MDファイルからの一括投入パターン

フロントマターで設定を書き、本文をテキストにする形式:

```markdown
---
account_id: ACCOUNT_ID
scenario_id: SCENARIO_ID
channel: mail
type: step
send_type: scheduled
send_date: 2
send_hour: 18
send_min: 0
title: 3通目：2日後18時
from_mail: info@example.com
from_name: 送信者名
subject: 【Day2】件名
---
本文テキストをここに書く

配信解除: %cancel%
```

AIはこのMDを読み取り、フロントマターをAPIパラメータに変換して `message_create` ツールで送信する。

---

## 補足: REST API（curl）

```bash
# メッセージ一覧取得
curl -s "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/scenarios/SCENARIO_ID/messages?type=step&channel=mail&status=draft" \
  -H "Authorization: Bearer $UTAGE_API_KEY"

# メッセージ作成
curl -s -X POST "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/scenarios/SCENARIO_ID/messages" \
  -H "Authorization: Bearer $UTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @payload.json

# メッセージ詳細取得
curl -s "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/scenarios/SCENARIO_ID/messages/MESSAGE_ID" \
  -H "Authorization: Bearer $UTAGE_API_KEY"

# メッセージ更新（PUT: 全フィールド必須。title/use_ab_test/action_id/shorten_domain/shorten_type/conditions/url_actions/mail等を省略しない）
curl -s -X PUT "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/scenarios/SCENARIO_ID/messages/MESSAGE_ID" \
  -H "Authorization: Bearer $UTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @payload.json

# メッセージ削除
curl -s -X DELETE "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/scenarios/SCENARIO_ID/messages/MESSAGE_ID" \
  -H "Authorization: Bearer $UTAGE_API_KEY"
```

2026-05-16 実操作確認:
- MCP `message_create` で `channel=mail` / `channel=line` の下書き作成成功
- REST `POST /accounts/{account_id}/scenarios/{scenario_id}/messages` でメール下書き作成成功
- REST `GET` / `PUT /accounts/{account_id}/scenarios/{scenario_id}/messages/{message_id}` 成功
- 2026-06-08 MCP `find_tools(category="message")` で message 系31ツールを確認
- 2026-06-08 MCP `message_list` / `message_get` / `message_action_list` の読み取り動作を確認
- 2026-06-08 RESTで `use_ab_test: 1` + `mail.subject_pattern_b` を既存ステップに反映し、件名ABテスト保存を確認
