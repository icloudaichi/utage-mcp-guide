# UTAGE AI Skill - media

UTAGE内にアップロードされた通常メディア・動画・音声のURL取得とアップロードを扱います。
通常メディア・動画・音声はいずれもMCPの署名付きURLフローでアップロード可能です。

## MCPツール

| ツール名 | 操作 |
|:---|:---|
| `media_list` | 通常メディア一覧取得（keyword / folder_id で絞り込み可） |
| `media_folder_list` | 通常メディアフォルダ一覧 |
| `media_upload_url` | 通常メディアの署名付きアップロードURL発行 |
| `media_complete` | 通常メディアアップロード完了通知 |
| `media_video_list` | 動画一覧取得（keyword / folder_id で絞り込み可） |
| `media_video_folder_list` | 動画フォルダ一覧 |
| `media_video_upload_url` | 動画の署名付きアップロードURL発行 |
| `media_video_complete` | 動画アップロード完了通知 |
| `media_audio_list` | 音声一覧取得 |
| `media_audio_folder_list` | 音声フォルダ一覧 |
| `media_audio_upload_url` | 音声の署名付きアップロードURL発行 |
| `media_audio_complete` | 音声アップロード完了通知 |

---

## ⚠️ 注意点

> → 全カテゴリ共通トラップはルートの SKILL.md を参照

- 取得したURLをページ要素で使う場合: `video_id` は NG。必ず **`video_url`（絶対パスURL）** を使うこと
- `*_upload_url` はサーバー側にメディアIDを作成するため、AIが自律実行する場合は事前に確認を取ること
- `presigned_post.url` と `presigned_post.fields` は署名付き情報。短時間で失効し、機密性もあるためログやドキュメントへそのまま残さないこと
- アップロード後は必ず対応する `*_complete(media_id)` を呼ぶこと。完了通知しないと管理画面に反映されない可能性があります

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

## MCPアップロードの実操作フロー

2026-05-16 にREST/MCPの両方で画像アップロードを確認済み。

基本形:

1. `*_upload_url(filename, filetype)` で `media_id` と `presigned_post` を取得
2. `presigned_post.url` に対して `fields` と `file` を multipart POST
3. ストレージ側の成功レスポンスを確認
4. 対応する `*_complete(media_id)` を呼ぶ
5. 対応する `*_list(keyword)` で反映を確認

カテゴリ別:

| 種別 | URL発行 | 完了通知 | 確認 |
|:---|:---|:---|:---|
| 通常メディア | `media_upload_url` | `media_complete` | `media_list` |
| 動画 | `media_video_upload_url` | `media_video_complete` | `media_video_list` |
| 音声 | `media_audio_upload_url` | `media_audio_complete` | `media_audio_list` |

REST API:

1. `POST /media/upload-url` に `filename`, `filetype`, 任意で `folder_id` を送って `media_id` と `presigned_post` を取得
2. `presigned_post.url` に対して `fields` と `file` を multipart POST
3. ストレージ側が HTTP 204 を返す
4. `POST /media/complete` に `{"media_id":"..."}` を送る
5. `GET /media?keyword=...` で反映を確認

`POST /media/{media_id}/complete`, `PUT /media/{media_id}/complete`, `POST /media/upload-complete`, `POST /media/complete-upload` は 404。正しいREST完了通知は `POST /media/complete`。

2026-06-08 実操作確認:
- MCP `find_tools(category="media")` で media 系12ツールを確認
- MCP `media_list` / `media_folder_list` / `media_video_list` / `media_video_folder_list` / `media_audio_list` / `media_audio_folder_list` の読み取り動作を確認
