# UTAGE AI Skill - media

UTAGE内にアップロードされた通常メディア・動画・音声のURLを取得します。
通常メディア（画像等）はREST APIまたはMCPの署名付きURLフローでアップロード可能です。
動画・音声アップロードは引き続き管理画面または別補助スクリプトで扱います。

## MCPツール

| ツール名 | 操作 |
|:---|:---|
| `media_list` | 通常メディア一覧取得（keyword / folder_id で絞り込み可） |
| `media_folder_list` | 通常メディアフォルダ一覧 |
| `media_upload_url` | 通常メディアの署名付きアップロードURL発行 |
| `media_complete` | 通常メディアアップロード完了通知 |
| `media_video_list` | 動画一覧取得（keyword / folder_id で絞り込み可） |
| `media_video_folder_list` | 動画フォルダ一覧 |
| `media_audio_list` | 音声一覧取得 |
| `media_audio_folder_list` | 音声フォルダ一覧 |

---

## ⚠️ 注意点

> → 全カテゴリ共通トラップはルートの SKILL.md を参照

- 取得したURLをページ要素で使う場合: `video_id` は NG。必ず **`video_url`（絶対パスURL）** を使うこと
- `media_upload_url` はアップロード用URLとメディアIDを発行するため、AIが自律実行する場合は事前に確認を取ること
- アップロード後は必ず `media_complete(media_id)` を呼ぶこと。完了通知しないと管理画面に反映されない可能性があります
- 動画・音声のアップロードは `media_video_list` / `media_audio_list` ではできません

---

## 補足: REST API（curl）

```bash
# 通常メディア一覧
curl -s "https://api.utage-system.com/v1/media" \
  -H "Authorization: Bearer $UTAGE_API_KEY"

# 通常メディアフォルダ一覧
curl -s "https://api.utage-system.com/v1/media/folders" \
  -H "Authorization: Bearer $UTAGE_API_KEY"

# 動画一覧
curl -s "https://api.utage-system.com/v1/media/videos" \
  -H "Authorization: Bearer $UTAGE_API_KEY"

# 音声一覧
curl -s "https://api.utage-system.com/v1/media/audios" \
  -H "Authorization: Bearer $UTAGE_API_KEY"
```

## 通常メディアアップロードの実操作フロー

2026-05-16 にREST/MCPの両方で画像アップロードを確認済み。

REST API:

1. `POST /media/upload-url` に `filename`, `filetype`, 任意で `folder_id` を送って `media_id` と `presigned_post` を取得
2. `presigned_post.url` に対して `fields` と `file` を multipart POST
3. ストレージ側が HTTP 204 を返す
4. `POST /media/complete` に `{"media_id":"..."}` を送る
5. `GET /media?keyword=...` で反映を確認

MCP:

1. `media_upload_url(filename, filetype)` で `media_id` と `presigned_post` を取得
2. `presigned_post.url` に対して `fields` と `file` を multipart POST
3. `media_complete(media_id)` を呼ぶ
4. `media_list(keyword)` で反映を確認

`POST /media/{media_id}/complete`, `PUT /media/{media_id}/complete`, `POST /media/upload-complete`, `POST /media/complete-upload` は 404。正しいREST完了通知は `POST /media/complete`。

署名付きURL・署名フィールドは短時間で失効するため、ログやドキュメントへそのまま残さないこと。
