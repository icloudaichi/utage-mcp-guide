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

> MCPサーバー側のツール定義は頻繁に増えます。作業開始時に `find_tools` を呼び、現行カタログとプレビュー機能を確認してください。

| カテゴリ           | 参照先                  | MCPツール例                                                         |
| -------------- | -------------------- | --------------------------------------------------------------- |
| 🛡️ バックアップ     | `backup/SKILL.md`    | `funnel_list`, `funnel_page_get`, `message_list`, `message_get` |
| ステップメール・LINE配信 | `messages/SKILL.md`  | `message_create`, `message_update`                              |
| ファネル・LP・ページ要素  | `funnels/SKILL.md`   | `funnel_page_create`, `element_types_funnel`                    |
| シナリオ管理         | `scenarios/SKILL.md` | `message_scenario_create`                                       |
| 配信アカウント・ラベル・読者 | `accounts/SKILL.md`  | `message_account_list`, `message_label_create`                  |
| メディア参照・アップロード | `media/SKILL.md`     | `media_upload_url`, `media_video_upload_url`, `media_audio_upload_url` |
| エラー報告・フィードバック  | `report/SKILL.md`    | `report_discussion.py`                                          |


---

## ⚠️ 全カテゴリ共通の既知トラップ

> 実機検証で発見したエラー一覧です。AIはこれを参照してから操作してください。

### メッセージAPI


| #   | 症状                                   | 原因                                     | 正解                                                 |
| --- | ------------------------------------ | -------------------------------------- | -------------------------------------------------- |
| 1   | `validation_error: 送信タイプは必ず指定してください` | `send_type` を省略                        | `send_type: "scheduled"` or `"immediately"` を必ず付ける |
| 2   | 即時配信ステップを `reserved` に戻せない | `step_send_type: "immediately"` の安全制限に当たる | 既存値を確認し、必要なら `send_type: "immediately"` + `step_send_type: "none"` + `status: "reserved"` で復旧 |
| 3   | 予約済みメッセージの本文や件名を直接更新すると409 | `status=reserved` は直接更新不可 | まず `status: "draft"` へ変更し、全量PUT後に `reserved` へ戻す |
| 4   | `The X field must be present` | `message_update` で必須キー自体を省略 | `title`, `use_ab_test`, `action_id`, `shorten_domain`, `shorten_type`, `conditions`, `url_actions`, `mail/line/sms` は null/空配列でもキーを含める |
| 5   | ABテスト件名Bが保存されない | `use_ab_test` だけONにした | `use_ab_test: 1` と `mail.subject_pattern_b` をセットで送る |
| 6   | `channel` / `type` 変更で400 | 作成後変更不可のフィールドを書き換えた | 既存 `message_get` の値を維持する |


### ファネル要素 — プロパティ名の誤記


| #   | 要素            | ❌ 使えない                              | ✅ 正しい                                        | 症状            |
| --- | ------------- | ----------------------------------- | -------------------------------------------- | ------------- |
| 7   | `image`       | `image_src`                         | **`image_url`**                              | エラーなし・サイレント失敗 |
| 8   | `video`       | `video_id`                          | **`video_url`（絶対パスURL）**                     | 保存されない        |
| 9   | `table`       | `content`                           | **`body_rows` + `body_cols` + `table_data`** | キーが存在しない      |
| 10  | `deadline`    | `target_datetime`                   | **`target_type`（必須）+ `target_date`**         | 受け付けられない      |
| 11  | `accordion`   | `title`                             | **`content`（ヘッダー）+ `sub_content`**           | サイレント失敗       |
| 12  | `form-button` | `button_text` / `button_text_color` | **`content` / `color`**                      | サイレント失敗       |
| 13  | `text` | `color` プロパティに頼った | `content` 内のインラインスタイルで指定する | 色が反映されない |


### ページAPI


| #   | 症状                         | 原因              | 対策                            |
| --- | -------------------------- | --------------- | ----------------------------- |
| 14  | PUT後に他の要素がnullリセット         | 変更箇所だけ送った       | PUT前に必ずGETして全フィールド含めて送信       |
| 15  | `padding_top/bottom` が効かない | `section` に設定した | **`col`** に設定する               |
| 16  | 日本語JSONでエンコードエラー           | パイプで渡した         | `--data-binary @file` でファイル経由 |
| 17  | フォームが全幅に広がって崩れる | `pc_width=100` のページでフォーム親幅を絞っていない | 親 `row.width` を指定する |


### API制限


| #   | 症状・操作 | 原因・結果 | 対策 |
| --- | --- | --- | --- |
| 18  | `POST /actions` アクション作成 | **405 Method Not Allowed**（管理画面のみ） | `message_action_list` で既存アクションIDを取得して使う |
| 19  | シナリオ作成で `name` フィールド | **フィールド名は `title`** が正しい | `message_scenario_create(title=...)` を使う |
| 20  | HTMLメール要素を `properties` で包む | `properties` は定義レスポンス内のメタ情報 | **実データはフラットに書く** |
| 21  | LINE/メールの条件キーを推測で書く | 存在しないキーは失敗またはスキップされる | `message_condition_types` と `message_placeholder_list` で確認する |
| 22  | 読者一覧で `base_datetime` を使う | `base_datetime` は配信条件専用で読者検索ではスキップされる | 読者検索は `base_date` を使う |
| 23  | メディアアップロード後に完了通知しない | upload-url 発行だけでは反映が完了しない | 通常は `media_complete`、動画は `media_video_complete`、音声は `media_audio_complete` |


---

## このスキルについて

- **ライセンス**: MIT（スクリプト）/ CC BY 4.0（ドキュメント）
- **対象**: UTAGE 公式 MCPサーバー + REST API v1
- **メンテナー**: [@icloudaichi](https://github.com/icloudaichi)
- **バージョン**: 0.4.0（2026-06-08）
- **フィードバック**: [GitHub Discussions](https://github.com/icloudaichi/utage-mcp-guide/discussions)
