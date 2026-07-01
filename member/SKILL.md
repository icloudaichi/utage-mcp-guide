# UTAGE AI Skill - member

会員サイト、コース、レッスングループ、レッスンを扱います。
`member_*` は preview 扱いです。作業前に `find_tools(category="member")` と `element_types_lesson` を確認してください。

## MCPツール

| ツール名 | 操作 |
|:---|:---|
| `member_site_list` | 会員サイト一覧取得 |
| `member_course_list` | サイト配下のコース一覧取得 |
| `member_lesson_group_list` | コース配下のレッスングループ一覧取得 |
| `member_lesson_list` | コース配下のレッスン一覧取得 |
| `member_lesson_get` | レッスン詳細取得（element_id付き要素ツリー含む） |
| `member_lesson_create` | レッスン新規作成 |
| `member_lesson_update` | レッスン更新 |
| `member_lesson_delete` | レッスン削除 |
| `element_types_lesson` / `element_types_lesson_properties` | レッスン要素タイプ・プロパティ定義取得 |

---

## ⚠️ 注意点

> → 全カテゴリ共通トラップはルートの SKILL.md を参照

- **レッスン要素はファネル要素と別定義**。ファネルの `element_types_funnel` ではなく、必ず `element_types_lesson` を使うこと
- **階層は `section > row > col > コンテンツ要素`**。レッスンでもこの基本構造は同じ
- **`member_lesson_get` のレスポンスは `element_id` 付き**。更新時はこのIDを保持して、既存要素の同期に使う
- **参照系プロパティは作成時に指定しない**。`target_element_id` / `show_element_ids` / `hide_element_ids` / `related_element_id` は作成後に `member_lesson_update` で設定する
- **レッスン動画要素は `video_type` で必須キーが変わる**。YouTube/Vimeo/Loom は `video_url`、UTAGE内動画は `video_type: "app"` + `video_id`
- **`memo` はレッスン固有要素**。学習者の入力は `lesson_id + user_id + seq` に紐づくため、複製・並び替え時は意図しない保存先変更に注意する
- **削除は物理削除**。`member_lesson_delete` は自律実行せず、事前にバックアップと人間確認を取る

---

## レッスン要素の最小構造

```json
[
  {
    "type": "section",
    "children": [
      {
        "type": "row",
        "children": [
          {
            "type": "col",
            "children": [
              {
                "type": "text",
                "content": "<p>本文</p>"
              }
            ]
          }
        ]
      }
    ]
  }
]
```

## 動画要素の使い分け

YouTubeなど外部動画:

```json
{
  "type": "video",
  "video_type": "YouTube",
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "show_controls": 1
}
```

UTAGE内動画:

```json
{
  "type": "video",
  "video_type": "app",
  "video_id": "MEDIA_VIDEO_ID",
  "show_controls": 1
}
```

## 実操作確認

2026-07-01 実操作確認:
- MCP `find_tools(category="member")` で member 系8ツールを確認
- MCP `member_site_list` / `member_course_list` / `member_lesson_group_list` / `member_lesson_list` の読み取り動作を確認
- MCP `member_lesson_get` でレッスン詳細と `element_id` 付き要素ツリーを確認
- MCP `element_types_lesson` でレッスン要素20種類を確認
- MCP `element_types_lesson_properties(types="text,video,memo")` で、`memo` 要素と `video_type: "app"` 時の `video_id` 要件を確認
