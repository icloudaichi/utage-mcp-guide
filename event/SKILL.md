# UTAGE AI Skill - event

イベント、日程、カレンダー、担当者、申込者、申込フォームを扱います。
`event_*` は preview 扱いです。作業前に `find_tools(category="event")` で最新スキーマを確認してください。

## MCPツール

| ツール名 | 操作 |
|:---|:---|
| `event_list` / `event_get` | イベント一覧・詳細取得 |
| `event_create` / `event_update` / `event_delete` | イベントCRUD |
| `event_schedule_list` / `event_schedule_get` | イベント日程一覧・詳細取得 |
| `event_schedule_create` / `event_schedule_update` / `event_schedule_delete` | セミナー日程CRUD |
| `event_calendar_get` / `event_calendar_update` | 個別相談・個別予約のカレンダー設定取得・部分更新 |
| `event_member_list` | 面談担当者マスター一覧取得 |
| `event_applicant_list` / `event_applicant_get` | 申込者一覧・詳細取得 |
| `event_applicant_update` | 申込者の参加状況・成約状況・項目の部分更新 |
| `event_form_item_get` / `event_form_item_update` | 申込フォーム・申込者項目定義の取得・更新 |

---

## イベントタイプ

| type | 日程の作り方 | 主なツール |
|:---|:---|:---|
| `seminar` | 管理者が候補日程を事前作成 | `event_schedule_*` |
| `calendar` | 受付枠から予約者が選び、予約確定時に日程を自動生成 | `event_calendar_get/update` |

## ⚠️ 注意点

> → 全カテゴリ共通トラップはルートの SKILL.md を参照

- **`type` と `use_line_event` は作成後変更不可**。`event_update` はそれ以外の指定フィールドだけを部分更新する
- **リマインダありの作成は非同期になる場合がある**。`event_get` の `reminder_scenario_copy_status` が `complete` になるまで申込URLを配布しない
- **`calendar` は作成後の設定が必要**。`event_calendar_update` で担当者や受付枠を設定してから予約受付を開始する
- **`event_schedule_create/update/delete` は `seminar` 専用**。`calendar` の日程は予約確定時に自動生成される
- **日程の開始・終了は同一日**。更新時に日時を変える場合は `start_datetime` と `end_datetime` を両方指定する
- **セミナー開始日時の変更は予約者のリマインダ配信日時を再計算する**。予約者が多い場合は応答に時間がかかる
- **カレンダーの配列項目は全件置換**。`members` / `day_of_week_schedules` は指定時に全件置換され、`specified_date_schedules` は本日以降の設定が置換される
- **空き枠はMCPの設定だけでは確定しない**。担当者個別の受付枠やGoogleカレンダー予定で、公開予約枠がさらに除外される場合がある
- **申込者の氏名・メール・電話・住所は読み取り専用**。`event_applicant_update` では参加状況・成約状況・使用中の申込者項目などを更新する
- **参加状況の変更には副作用がある**。キャンセル系への変更で配信停止、キュー更新、通知、キャンセルシナリオ登録が発生し得る。通知・配信フラグは必要な場合だけ明示する
- **申込者一覧の未入力氏名に注意**。`name` / `kana` は未入力でも半角スペースになる場合があるため、空白を除去して判定する。LINEのみイベントでは `mail` が `null` の場合がある
- **申込フォームの `items` は完全なリスト**。`event_form_item_update` で省いた項目は未使用になり、配列順が表示順になる。更新前に `event_form_item_get` で現在値を取得する
- **イベント削除後も既存予約者へのリマインダは自動停止しない**。配布済みキャンセルページも無効になるため、削除は人間確認後に行う
- **個人情報を検証ログへ残さない**。申込者系の確認結果は件数とフィールド構造だけを記録する

## 安全な参照フロー

1. `event_list` でイベントIDとタイプを確認する
2. `event_get` で基本設定とリマインダコピー状態を確認する
3. `seminar` は `event_schedule_list`、`calendar` は `event_calendar_get` を使う
4. 必要な場合だけ `event_member_list`、`event_form_item_get` を参照する
5. 申込者情報は目的と権限を確認してから `event_applicant_list/get` を呼ぶ

## 検証記録

2026-08-22 カタログ確認:
- MCP `find_tools(category="event")` で event 系18ツールを確認
- 全18ツールの公開スキーマ、preview状態、イベントタイプ別制約、副作用を確認
- 作成・更新・削除および申込者データ取得は未実行
