---
name: utage-mcp-guide
description: >
  UTAGEのMCPサーバーを安全に使うためのコミュニティ知見ベース。
  実機検証で発見したサイレント失敗・プロパティ名の罠を回避し、
  AIでUTAGE操作を自動化します。
requires:
  - UTAGEのMCPサーバー接続（setup/SKILL.md を参照）
---

# UTAGE AI Skill

> MCPサーバーに接続すればツール定義は手に入る。  
> しかしサイレント失敗やプロパティ名の罠は、踏んだ人にしかわからない。  
> このスキルはその知見を集めて、全員が同じ穴に落ちないようにするプロジェクトです。  
> エラー・新発見はぜひ [GitHub Discussions](https://github.com/icloudaichi/utage-mcp-guide/discussions) へ。

---

## 初回セットアップ

MCPサーバーに未接続の場合は先にセットアップを完了してください:

```
setup/ フォルダの SKILL.md を参照してください
```

---

## 操作カテゴリ

目的に応じて対応するサブスキルを読み込んでください:

> MCPサーバー側のツール定義は頻繁に増えます。作業開始時に `find_tools(category="...")` を呼び、現行カタログとプレビュー機能を確認してください。`query` は現在、結果の絞り込みには使われません。

| カテゴリ           | 参照先                  | MCPツール例                                                         |
| -------------- | -------------------- | --------------------------------------------------------------- |
| 🛡️ バックアップ     | `backup/SKILL.md`    | `funnel_list`, `funnel_page_get`, `message_list`, `message_get` |
| ステップメール・LINE配信 | `messages/SKILL.md`  | `message_create`, `message_update`                              |
| ファネル・LP・ページ要素  | `funnels/SKILL.md`   | `funnel_page_create`, `element_types_funnel`                    |
| シナリオ管理         | `scenarios/SKILL.md` | `message_scenario_create`                                       |
| 配信アカウント・ラベル・読者 | `accounts/SKILL.md`  | `message_account_list`, `message_label_create`                  |
| メディア参照・アップロード | `media/SKILL.md`     | `media_upload_url`, `media_video_upload_url`, `media_audio_upload_url` |
| 会員サイト・レッスン | `member/SKILL.md`    | `member_site_list`, `member_lesson_get`, `element_types_lesson` |
| 商品・価格ラインナップ | `payment/SKILL.md` | `payment_product_list`, `payment_product_detail_list` |
| イベント・予約管理 | `event/SKILL.md` | `event_list`, `event_schedule_list`, `event_applicant_list` |
| エラー報告・フィードバック  | `report/SKILL.md`    | `report_discussion.py`                                          |

2026-10-03 LBS接続の `find_tools` メタデータ（入力/出力スキーマ・annotationsは未取得）:

| カテゴリ | 件数 | 8月からの増分 |
|:---|---:|:---|
| `funnel` | 32 | +9 |
| `message` | 102 | +31 |
| `media` | 15 | +3 |
| `member` | 48 | +24 |
| `event` | 29 | +11 |
| `payment` | 17 | +17 |
| `reference` | 8 | 0 |
| `integration` | 2 | +1 |
| **合計** | **253** | **+96** |

`find_tools` 自体は除きます。全253件の分類・提供状態・実read/未実行は [docs/tool-catalog.md](docs/tool-catalog.md) に記録しています。`find_tools` は名前・説明を発見する手段であり、入力schema確認を代替しません。現行クライアントの定義を確認し、readで認証対象を照合します。今回の契約テスト成功と本番API成功は区別してください。

`reference` / `integration` の全ツール:

| ツール名 | 用途 |
|:---|:---|
| `element_types_funnel` / `element_types_funnel_properties` | ファネル要素タイプ・プロパティ定義 |
| `element_types_lesson` / `element_types_lesson_properties` | レッスン要素タイプ・プロパティ定義 |
| `element_types_mail` / `element_types_mail_properties` | HTMLメール要素タイプ・プロパティ定義 |
| `message_types_line` | LINEメッセージタイプ定義 |
| `message_condition_types` | 配信条件タイプ定義 |
| `google_spreadsheet_account_list` | Googleスプレッドシート連携アカウント一覧 |
| `ads_setting_list` | 広告連携設定一覧 |

2026-08-22には `funnel_list`、`message_account_list`、`media_list`、`member_site_list`、`event_list`、`google_spreadsheet_account_list`、`element_types_funnel` の読み取り応答を確認しました。当時は個人情報を返し得る一覧を検証対象から除外しました。2026-10-03は最小readの共有証跡を再利用し、値を除去して [検証記録](docs/endpoint-testing.md) に残しています。

---

## ⚠️ 全カテゴリ共通の既知トラップ

> 実機検証で発見したエラー一覧です。AIはこれを参照してから操作してください。

### メッセージAPI


| #   | 症状                                   | 原因                                     | 正解                                                 |
| --- | ------------------------------------ | -------------------------------------- | -------------------------------------------------- |
| 1   | `validation_error: 送信タイプは必ず指定してください` | `send_type` を省略                        | `send_type: "scheduled"` or `"immediately"` を必ず付ける |
| 2   | 即時配信ステップを `reserved` に戻せない | `step_send_type: "immediately"` の安全制限に当たる | 既存値を確認し、必要なら `send_type: "immediately"` + `step_send_type: "none"` + `status: "reserved"` で復旧 |
| 3   | `sending` / `completed` のメッセージを更新すると409 | 配信中・配信済みは更新不可 | `draft` / `reserved` の間に更新する。`reserved` の日時・条件・ABテスト変更時はキューが自動再作成される |
| 4   | 配列項目を一部だけ送って既存値が消える | `conditions` / `url_actions` / `line.messages` は指定時に全件置換 | 既存値を維持する場合は省略し、変更する場合は完成した配列を送る |
| 5   | ABテスト件名Bが保存されない | `use_ab_test` だけONにした | `use_ab_test: 1` と `mail.subject_pattern_b` をセットで送る |
| 6   | `channel` / `type` 変更で400 | 作成後変更不可のフィールドを書き換えた | 既存 `message_get` の値を維持する |


### ファネル要素 — プロパティ名の誤記


| #   | 要素            | ❌ 使えない                              | ✅ 正しい                                        | 症状            |
| --- | ------------- | ----------------------------------- | -------------------------------------------- | ------------- |
| 7   | `image`       | `image_src`                         | **`image_url`**                              | エラーなし・サイレント失敗 |
| 8   | ファネル `video` | `video_id`                          | **`video_url`（絶対パスURL）**                     | 保存されない        |
| 9   | `table`       | `content`                           | **`body_rows` + `body_cols` + `table_data`** | キーが存在しない      |
| 10  | `deadline`    | `target_datetime`                   | **`target_type`（必須）+ `target_date`**         | 受け付けられない      |
| 11  | `accordion`   | `title`                             | **`content`（ヘッダー）+ `sub_content`**           | サイレント失敗       |
| 12  | `form-button` | `button_text` / `button_text_color` | **`content` / `color`**                      | サイレント失敗       |
| 13  | `text` | `color` プロパティに頼った | `content` 内のインラインスタイルで指定する | 色が反映されない |


### ページAPI


| #   | 症状                         | 原因              | 対策                            |
| --- | -------------------------- | --------------- | ----------------------------- |
| 14  | ページ更新で他の要素が消える | `elements` は指定時に配列全体が置換される | 更新前にGETし、変更後の全要素を `elements` に含める |
| 15  | `padding_top/bottom` が効かない | `section` に設定した | **`col`** に設定する               |
| 16  | 日本語JSONでエンコードエラー           | パイプで渡した         | `--data-binary @file` でファイル経由 |
| 17  | フォームが全幅に広がって崩れる | `pc_width=100` のページでフォーム親幅を絞っていない | 親 `row.width` を指定する |


### API制限


| #   | 症状・操作 | 原因・結果 | 対策 |
| --- | --- | --- | --- |
| 18  | 配信アクションとファネルアクションを混同する | 現行MCPは両方のCRUDに対応するが別リソース | 配信後処理は `message_action_*`、フォーム・決済後処理は `funnel_action_*` を使う |
| 19  | シナリオ作成で `name` フィールド | **フィールド名は `title`** が正しい | `message_scenario_create(title=...)` を使う |
| 20  | HTMLメール要素を `properties` で包む | `properties` は定義レスポンス内のメタ情報 | **実データはフラットに書く** |
| 21  | LINE/メールの条件キーを推測で書く | 存在しないキーは失敗またはスキップされる | `message_condition_types` と `message_placeholder_list` で確認する |
| 22  | 読者一覧で `base_datetime` を使う | `base_datetime` は配信条件専用で読者検索ではスキップされる | 読者検索は `base_date` を使う |
| 23  | メディアアップロード後に完了通知しない | upload-url 発行だけでは反映が完了しない | 通常は `media_complete`、動画は `media_video_complete`、音声は `media_audio_complete` |
| 24  | 会員サイトレッスンの動画要素でファネルのルールを流用する | レッスン `video` は `video_type` により必須キーが変わる | YouTube/Vimeo/Loom は `video_url`、UTAGE内動画は `video_type: "app"` + `video_id` |


---

## このスキルについて

- **ライセンス**: MIT（スクリプト）/ CC BY 4.0（ドキュメント）
- **対象**: UTAGE 公式 MCPサーバー + REST API v1
- **メンテナー**: [@icloudaichi](https://github.com/icloudaichi)
- **バージョン**: 0.7.0（2026-10-03）
- **フィードバック**: [GitHub Discussions](https://github.com/icloudaichi/utage-mcp-guide/discussions)
