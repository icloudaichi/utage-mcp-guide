# UTAGE AI Skill - funnels

ファネル・ステップ・ページの作成・編集・削除を行います。

## MCPツール

| ツール名 | 操作 |
|:---|:---|
| `funnel_list` / `funnel_create` / `funnel_update` | ファネルCRUD |
| `funnel_step_list` / `funnel_step_create` / `funnel_step_update` | ステップCRUD |
| `funnel_step_reorder` | ステップ並び替え |
| `funnel_page_list` / `funnel_page_get` | ページ取得 |
| `funnel_page_create` / `funnel_page_update` / `funnel_page_delete` | ページCRUD |
| `funnel_action_list` / `funnel_action_get` | ファネルアクション一覧・詳細取得 |
| `funnel_action_create` / `funnel_action_update` / `funnel_action_delete` | ファネルアクションCRUD |
| `funnel_action_group_list` | アクション整理用グループ一覧取得 |
| `funnel_stats_get` / `funnel_stats_daily` | ファネル統計取得 |
| `funnel_subscriber_list` | ファネル登録者一覧取得 |
| `funnel_tracking_list` / `funnel_tracking_stats` | 登録経路一覧・集計 |
| `element_types_funnel` / `element_types_funnel_properties` | 要素タイプ定義取得 |

---

## データ構造

```
ファネル
 └── ステップ（公開URLを持つ）
      └── ページ（A/Bテスト時に複数可）
           └── 要素（section > row > col > コンテンツ要素）
```

---

## ⚠️ 注意点

> → 全カテゴリ共通トラップ（プロパティ名の罠 #3〜#8）はルートの SKILL.md を参照

### ファネル固有の注意

- **要素の階層ルール**: section の直下に text 等を置くのは NG。必ず `section > row > col > コンテンツ要素` の順
- **`padding_top` / `padding_bottom` は `col` に設定する**（section に設定しても効かない）
- **ページ更新は部分更新**。省略フィールドは維持されるが、`elements` を指定すると配列全体が置換されるため、必ず `funnel_page_get` で現在の要素を取得してから編集する
- **ファネルアクションと配信アクションは別物**。フォーム送信・決済完了後の処理は `funnel_action_*`、メッセージ配信後の処理は `message_action_*` を使う
- **日本語を含む JSON** は `--data-binary @file` で送信（パイプ経由はエンコードエラーの可能性）
- **`content_type` は作成後に変更不可**。`elements` と `raw_html` は作成時に選ぶ
- **`raw_html` は html/head/body タグ必須**。DOCTYPEは任意、最大4MB
- **全幅ページ（`pc_width=100`）の背景色**はページの `background_color` で指定する。固定幅ページでは指定すると表示が崩れる場合があります
- **全幅ページのコンテンツ幅**は `section.content_width` ではなく `row.width` で制御する
- **ステップ並び替え**は全ステップID必須。ID不足・重複・余分ID・空配列は422
- **フォーム付きLP**は現行実機では `form` 要素に `scenario_id` と `use_reader_item=1` を指定する方式が安定。`form-name` / `form-email` は未対応
- **統計/登録者系は preview**。`funnel_subscriber_list` は氏名・連絡先を返す可能性があるため、検証ログには件数やフィールド構造だけ残す

---

## ページ作成の要素構造サンプル

`funnel_page_create` の `elements` パラメータ:

```json
[
  {
    "type": "section",
    "children": [{
      "type": "row",
      "children": [{
        "type": "col",
        "padding_top": 60,
        "padding_bottom": 60,
        "children": [
          {"type": "text", "content": "<h1>見出しテキスト</h1>"},
          {
            "type": "image",
            "image_url": "https://example.com/image.jpg"
          },
          {
            "type": "button",
            "content": "申し込む",
            "button_color": "btn-green",
            "color": "#ffffff",
            "link_type": "url",
            "link_url": "https://example.com/apply"
          }
        ]
      }]
    }]
  }
]
```

---

## 要素タイプ定義の確認

使用可能な要素とプロパティは MCPツールで取得できます:

```
element_types_funnel                    → 基本要素タイプ一覧
element_types_funnel(include="form,payment,event,webinar") → 拡張カテゴリも含む
element_types_funnel_properties(types="text,button,image") → プロパティ定義
```

HTMLメール要素は `element_types_mail` / `element_types_mail_properties` を使う。ファネル要素とメール要素は似ていますが、使えるプロパティが異なるため混在させないでください。

`element_types_funnel_properties` のレスポンスには `global_common_properties` と `content_common_properties` が含まれます。個別要素の `properties` はその要素固有の定義で、作成・更新時のデータを `properties` キーで包む意味ではありません。

## フォーム付きLPの現行実機パターン

```json
{
  "type": "form",
  "scenario_id": "SCENARIO_ID",
  "use_reader_item": 1,
  "label": "show",
  "required": 1,
  "content": "登録する",
  "button_color": "btn-green",
  "color": "#ffffff"
}
```

`form-input` / `form-button` は要素タイプとして存在しますが、通常登録フォームでは `form.children` に入れず、`form` 要素自体にボタン・読者項目利用設定を持たせます。
公開フォーム送信は `/form/action/{page_id}` で動作しますが、これは公式REST APIではなく公開ページ内部動作です。

---

## 補足: REST API（curl）

```bash
# ファネル一覧取得
curl -s "https://api.utage-system.com/v1/funnels" \
  -H "Authorization: Bearer $UTAGE_API_KEY"

# ファネル作成
curl -s -X POST "https://api.utage-system.com/v1/funnels" \
  -H "Authorization: Bearer $UTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "ファネル名"}'

# ステップ一覧取得（step_url を含む）
curl -s "https://api.utage-system.com/v1/funnels/FUNNEL_ID/steps" \
  -H "Authorization: Bearer $UTAGE_API_KEY"

# ステップ並び替え（全ステップID必須）
curl -s -X PATCH "https://api.utage-system.com/v1/funnels/FUNNEL_ID/steps/reorder" \
  -H "Authorization: Bearer $UTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"step_ids":["STEP_ID_1","STEP_ID_2","STEP_ID_3"]}'

# ページ作成
curl -s -X POST \
  "https://api.utage-system.com/v1/funnels/FUNNEL_ID/steps/STEP_ID/pages" \
  -H "Authorization: Bearer $UTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @page.json

# ページ更新（⚠️ elementsを変更する場合はGETして全要素を含めること）
curl -s -X PATCH \
  "https://api.utage-system.com/v1/funnels/FUNNEL_ID/steps/STEP_ID/pages/PAGE_ID" \
  -H "Authorization: Bearer $UTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @updated_page.json
```

2026-06-08 実操作確認:
- MCP `element_types_funnel(include="form,payment,event,webinar")` と `element_types_funnel_properties` の読み取り動作を確認

2026-08-22 カタログ確認:
- MCP `find_tools(category="funnel")` で funnel 系23ツールを確認
- `funnel_action_list/create/get/update/delete/group_list` の公開スキーマを確認（書き込み操作は未実行）

2026-07-01 実操作確認:
- MCP `funnel_list` / `funnel_step_list` / `funnel_page_list` / `funnel_tracking_list` の読み取り動作を確認
- MCP `funnel_stats_get` / `funnel_stats_daily` / `funnel_tracking_stats` の読み取り動作を確認
- MCP `funnel_subscriber_list` はテスト用ファネルで0件レスポンスを確認（PIIなし）
