# UTAGE AI Skill - backup

UTAGEのファネルデータおよび配信データ（シナリオ・ステップメール・LINE配信）を
階層構造のままローカルにバックアップします。

## いつ使うか

- 「UTAGEのバックアップを取って」
- 「ファネルをバックアップして」
- 「シナリオのバックアップを取って」
- 「ステップメールをバックアップして」
- 作業前に復元ポイントを作りたいとき

---

## 🚀 推奨: スクリプトによる一括バックアップ

> **MCPツール経由のバックアップは非推奨です。**  
> ファネル数が多い場合（10件以上）、MCPツールでは1件ずつAPI呼び出しが必要で  
> AIのコンテキスト上限に達します。以下のスクリプト方式を使ってください。

### Step 1: APIキーのセットアップ

```bash
python3 backup/scripts/setup_apikey.py
```

対話形式でUTAGEのAPIキーを入力すると、以下に保存されます:

```
~/.utage-mcp-guide/.env
```

> ⚠️ **セキュリティに関する重要な注意**
> 
> - APIキーは **ホームディレクトリ（`~/.utage-mcp-guide/`）** に保存されます
> - **プロジェクトフォルダ内には絶対に保存しないでください**
> - プロジェクト内に `.env` を置くと、Git push で平文のAPIキーが  
>   公開リポジトリにアップロードされる事故が起きます
> - `.gitignore` に `.env` は含まれていますが、万が一の二重防御として  
>   プロジェクト外に保存する設計にしています
> - ファイルのパーミッションは `600`（owner のみ読み書き可）に設定されます

**APIキーの取得方法:**

1. UTAGEの管理画面にログイン
2. 左メニュー → **API設定**
3. APIキーをコピー

### Step 2: バックアップの実行

```bash
# 全ファネルをバックアップ
python3 backup/scripts/backup_funnels.py

# 名前で絞り込み
python3 backup/scripts/backup_funnels.py --name "サンプル"

# 出力先を指定
python3 backup/scripts/backup_funnels.py --output ./my_backup
```

出力先には `backup_YYYY-MM-DD/` フォルダが作成され、
全ファネル・ステップ・ページがMarkdownファイルで保存されます。
2026-10-03 以降のスクリプトは、ファネル・ステップのディレクトリ名とページのファイル名を `{サニタイズ済み名称}__{リソースIDのSHA-256ハッシュ}` とします。同名や、ID に `/`・`:` 等が含まれる場合の上書きを避けます。ハッシュは UTF-8 の元 ID から計算した64桁の16進数で、元 ID は各ファイルのフロントマターに保存します。ステップの `status` はページ一覧と全ページ詳細の取得が成功した場合のみ `complete`、失敗があれば `incomplete` になり `errors` を記録します。

### スクリプト一覧

| ファイル | 説明 |
|:---|:---|
| `scripts/setup_apikey.py` | APIキーの入力・保存（初回のみ） |
| `scripts/backup_funnels.py` | ファネルの一括バックアップ |

---

## MCPツール経由のバックアップ（少数ファネル向け）

ファネル数が少ない場合（10件未満）や、特定のファネル1つだけバックアップしたい場合は、
AIにMCPツール経由で実行を依頼できます。

AIは以下の手順で実行します:

1. `funnel_list` → `funnel_step_list` → `funnel_page_list` → `funnel_page_get`
2. 取得したデータを下記フォーマットのMarkdownに変換

> ⚠️ 10件以上のファネルがある場合は、上記のスクリプト方式を使ってください。
> MCPツールは1件ずつAPI呼び出しが必要で、コンテキスト上限に達します。

---

## 出力フォーマット

各ファイルは **Markdownファイル** で保存します。  
メタデータはファイルの YAML フロントマター（ヘッダ）に格納し、  
データ本体は本文に JSON / HTML コードブロックで記録します。

### フォルダ構造（全体）

```
backup_YYYY-MM-DD/
│
├── funnels/                          ← ファネル系
│   ├── {ファネル名}__{IDハッシュ}/
│   │   ├── _meta.md                 ← ファネルのメタデータ
│   │   ├── {ステップ名}__{IDハッシュ}/
│   │   │   ├── _meta.md             ← ステップのメタデータ
│   │   │   ├── {ページタイトル}__{IDハッシュ}.md  ← ページの要素データ
│   │   │   └── {ページタイトル}__{IDハッシュ}.md
│   │   └── {ステップ名}__{IDハッシュ}/
│   │       └── ...
│   └── {ファネル名}__{IDハッシュ}/
│       └── ...
│
├── messages/                         ← 配信系
│   ├── {アカウント名}/
│   │   ├── _meta.md                 ← アカウントのメタデータ
│   │   ├── {シナリオ名}/
│   │   │   ├── _meta.md             ← シナリオのメタデータ
│   │   │   ├── 001_{メッセージ管理名}.md  ← メッセージデータ
│   │   │   ├── 002_{メッセージ管理名}.md
│   │   │   └── ...
│   │   └── {シナリオ名}/
│   │       └── ...
│   └── {アカウント名}/
│       └── ...
│
└── _backup_summary.md               ← 全体サマリー
```

---

## Part 1: ファネルのバックアップ

### ファネルの `_meta.md`

```markdown
---
type: funnel
id: "FUNNEL_ID_SAMPLE"
name: "サンプルファネル"
created_at: "2024-06-27 10:23:32"
updated_at: "2025-11-13 13:25:11"
backed_up_at: "2026-04-27T14:00:00+09:00"
steps_count: 4
---

# ファネル: サンプルファネル

| 項目 | 値 |
|:---|:---|
| ID | FUNNEL_ID_SAMPLE |
| 作成日 | 2024-06-27 |
| 更新日 | 2025-11-13 |
| ステップ数 | 4 |
```

### ステップの `_meta.md`

```markdown
---
type: step
id: "STEP_ID_SAMPLE"
funnel_id: "FUNNEL_ID_SAMPLE"
name: "登録ページ"
step_url: "https://example.com/p/STEP_ID_SAMPLE"
order: 0
backed_up_at: "2026-04-27T14:00:00+09:00"
pages_count: 1
---

# ステップ: 登録ページ

| 項目 | 値 |
|:---|:---|
| ID | STEP_ID_SAMPLE |
| 公開URL | https://example.com/p/STEP_ID_SAMPLE |
| 並び順 | 0 |
| ページ数 | 1 |
```

### ページの `.md`

```markdown
---
type: page
id: "PAGE_ID_SAMPLE"
funnel_id: "FUNNEL_ID_SAMPLE"
step_id: "STEP_ID_SAMPLE"
title: "サンプルページ"
content_type: "elements"
page_title: null
step_url: "https://example.com/p/STEP_ID_SAMPLE"
page_url: "https://example.com/page/PAGE_ID_SAMPLE"
pc_width: 100
background_color: "#ffffff"
is_no_index: 0
order: 0
is_archived: 0
created_at: "2024-06-27 10:23:32"
updated_at: "2024-06-27 10:23:32"
backed_up_at: "2026-04-27T14:00:00+09:00"
---

# ページ: サンプルページ

## ページ設定

| 項目 | 値 |
|:---|:---|
| コンテンツタイプ | elements |
| PC幅 | 100 |
| 背景色 | #ffffff |
| noindex | いいえ |

## 要素データ

```json
[
  {
    "type": "section",
    "children": [...]
  }
]
```

※ content_type が `raw_html` の場合は `html_source` をコードブロックで保存
```

---

## Part 2: 配信データのバックアップ

### アカウントの `_meta.md`

```markdown
---
type: account
id: "ACCOUNT_ID_SAMPLE"
name: "サンプル公式アカウント"
account_type: "mail_line"
created_at: "2022-09-28 14:08:28"
backed_up_at: "2026-04-27T14:00:00+09:00"
scenarios_count: 55
---

# 配信アカウント: サンプル公式アカウント

| 項目 | 値 |
|:---|:---|
| ID | ACCOUNT_ID_SAMPLE |
| タイプ | mail_line |
| 作成日 | 2022-09-28 |
| シナリオ数 | 55 |
```

### シナリオの `_meta.md`

```markdown
---
type: scenario
id: "SCENARIO_ID_SAMPLE"
account_id: "ACCOUNT_ID_SAMPLE"
title: "サンプルステップメール"
open_title: null
created_at: "2023-07-16 23:15:02"
backed_up_at: "2026-04-27T14:00:00+09:00"
messages_count: 5
---

# シナリオ: サンプルステップメール

| 項目 | 値 |
|:---|:---|
| ID | SCENARIO_ID_SAMPLE |
| 公開タイトル | — |
| 作成日 | 2023-07-16 |
| メッセージ数 | 5 |
```

### メッセージの `.md`

ファイル名: `{3桁連番}_{管理名}.md`（例: `001_vol.01.md`）  
連番は `send_date` → `send_hour` → `send_min` → `created_at` の順でソートして付与。

```markdown
---
type: message
id: "MESSAGE_ID_SAMPLE"
account_id: "ACCOUNT_ID_SAMPLE"
scenario_id: "SCENARIO_ID_SAMPLE"
channel: "mail"
message_type: "step"
status: "reserved"
title: "サンプルメール vol.03"
send_type: "scheduled"
step_send_type: "none"
send_date: 3
send_hour: 7
send_min: 0
use_ab_test: 0
shorten_domain: "example.com"
shorten_type: "shorten_url"
action_id: null
created_at: "2023-07-26 02:00:09"
updated_at: "2023-07-26 02:22:27"
backed_up_at: "2026-04-27T14:00:00+09:00"
---

# メッセージ: サンプルメール vol.03

## 配信設定

| 項目 | 値 |
|:---|:---|
| チャンネル | mail |
| タイプ | step |
| ステータス | reserved |
| 送信タイミング | 登録3日後 7:00 |
| ABテスト | なし |

## メール原稿

| 項目 | 値 |
|:---|:---|
| 件名 | サンプルメール vol.03 |
| 送信者名 | サンプル送信者 |
| 送信元メール | info@example.com |
| メールタイプ | html |

### 本文（elements）

```json
[
  {
    "type": "section",
    "children": [...]
  }
]
```

※ mail.type が `plain_text` の場合は `text` をそのままテキストブロックで保存

## 配信条件

```json
[]
```

## URLアクション

```json
[
  {
    "url": "https://example.com/p/STEP_ID_SAMPLE",
    "action_id": null,
    "expiration_type": "none"
  }
]
```
```

### LINE配信の場合

```markdown
---
type: message
id: "xxxx"
channel: "line"
message_type: "step"
# ... (共通フィールドは同じ)
---

## LINE原稿

### sender

| 項目 | 値 |
|:---|:---|
| sender_id | xxx（省略時はデフォルト送信者） |

### messages

```json
[
  {
    "type": "text",
    "text": "メッセージ本文"
  },
  {
    "type": "image",
    "image_url": "https://..."
  }
]
```
```

---

## 実行手順

AIは以下の手順でバックアップを実行してください。

### 1. 保存先フォルダの作成

- フォルダ名: `backup_YYYY-MM-DD`（実行日の日付）
- ユーザーが保存先を指定した場合はそちらに作成

### 2. 対象範囲の確認

ユーザーの指示に応じて範囲を決定:

| 指示 | 範囲 |
|:---|:---|
| 「バックアップ取って」 | **全部**（ファネル + 配信） |
| 「ファネルをバックアップ」 | ファネルのみ |
| 「シナリオをバックアップ」 | 配信のみ |
| 「○○のバックアップ」 | 名前で絞り込み |

### 3. ファネルのバックアップ（funnels/）

1. `funnel_list (per_page: 100)` で全件取得（ページネーション注意）
2. 各ファネルに対して:
   - `funnels/{ファネル名}/` フォルダ作成
   - `_meta.md` にファネル情報を記録
   - `funnel_step_list(funnel_id)` でステップ一覧取得
3. 各ステップに対して:
   - `{ステップ名}/` フォルダ作成
   - `_meta.md` にステップ情報を記録
   - `funnel_page_list(funnel_id, step_id)` でページ一覧取得
4. 各ページに対して:
   - `funnel_page_get(funnel_id, step_id, page_id)` で詳細取得
   - `.md` ファイルに保存（ファイル名 = `{title}.md`、空なら `page_{order}.md`）
   - `elements` → JSON / `html_source` → HTML でコードブロック保存
   - `pc_width`, `background_color`, `css`, `js_head`, `js_body` 等もフロントマター

### 4. 配信データのバックアップ（messages/）

1. `message_account_list` で全アカウント取得
2. 各アカウントに対して:
   - `messages/{アカウント名}/` フォルダ作成
   - `_meta.md` にアカウント情報を記録
   - `message_scenario_list(account_id)` でシナリオ一覧取得
3. 各シナリオに対して:
   - `{シナリオ名}/` フォルダ作成
   - `_meta.md` にシナリオ情報を記録
   - `message_list(account_id, scenario_id, per_page: 100)` でメッセージ一覧取得
4. 各メッセージに対して:
   - `message_get(account_id, scenario_id, message_id)` で詳細取得
   - `.md` ファイルに保存
   - ファイル名: `{3桁連番}_{title}.md`（連番は配信順序でソート）
   - チャンネルに応じて `mail` / `line` / `sms` の原稿を保存
   - `conditions`, `url_actions` も JSON コードブロックで保存

### 5. バックアップサマリーの作成

`_backup_summary.md` をルートに作成:

```markdown
---
type: backup_summary
backed_up_at: "2026-04-27T14:00:00+09:00"
total_funnels: 3
total_steps: 12
total_pages: 28
total_accounts: 2
total_scenarios: 10
total_messages: 45
---

# UTAGEバックアップサマリー

**実行日時:** 2026-04-27 14:00

## 統計

| カテゴリ | 項目 | 件数 |
|:---|:---|:---|
| ファネル | ファネル | 3 |
| | ステップ | 12 |
| | ページ | 28 |
| 配信 | アカウント | 2 |
| | シナリオ | 10 |
| | メッセージ | 45 |

## ファネル一覧

| # | ファネル名 | ステップ数 | ページ数 | 最終更新 |
|:---|:---|:---|:---|:---|
| 1 | サンプルファネル | 4 | 5 | 2025-11-13 |
| 2 | ... | ... | ... | ... |

## 配信アカウント一覧

| # | アカウント名 | タイプ | シナリオ数 | メッセージ数 |
|:---|:---|:---|:---|:---|
| 1 | サンプル公式アカウント | mail_line | 55 | 120 |
| 2 | ... | ... | ... | ... |
```

---

## ⚠️ 注意事項

2026-10-03 更新: `backup_funnels.py` の既定 URL を公式 `https://api.utage-system.com/v1` に修正しました。ファネル一覧はページごとの期待件数・総数・ID 重複を照合し、取得失敗や不整合は `_backup_manifest.json` に `incomplete` と記録して終了コード 1 を返します。エラー本文や認証情報はログへ出しません。
[ステップ一覧](https://docs.utage-system.com/api-reference/funnel/step-list)・[ページ一覧](https://docs.utage-system.com/api-reference/funnel/page-list) の公開仕様は `data` のみの非ページング形式です。未知の `meta`・`links` 等や重複 ID は仕様変化として拒否し、不完全な取得を完了扱いしません。
今回のバックアップ処理の検証は通信をモックした標準 Python の回帰テストのみです。実サービスのバックアップは実行していません。

- **API制限**: `funnel_page_get` と `message_get` はそれぞれ1件ずつ呼ぶ必要がある。大量データの場合は時間がかかる
- **ファイル名のサニタイズ**: タイトルに `/` `:` `?` `*` `"` `<` `>` `|` が含まれる場合は `_` に置換
- **アーカイブ済みページ**: `is_archived: 1` のページもバックアップ対象に含める
- **差分バックアップ**: 前回のバックアップが存在する場合、`updated_at` を比較して変更があったもののみ再取得する（ユーザーが「フルバックアップ」を指定した場合は全件取得）
- **メッセージの並び順**: ステップメールは `send_date` → `send_hour` → `send_min` 順、ブロードキャストは `send_date` の日付順でソートして連番を付ける

---

## 復元について

### ファネルの復元

1. `_meta.md` のフロントマターからファネル・ステップ・ページの設定を読み取る
2. `.md` ファイルの JSON/HTML コードブロックから要素データを読み取る
3. `funnel_create` → `funnel_step_create` → `funnel_page_create` の順で再作成

### 配信データの復元

1. アカウント・シナリオの `_meta.md` から設定を読み取る
2. メッセージの `.md` からフロントマターの配信設定と本文データを読み取る
3. `message_account_create` → `message_scenario_create` → `message_create` の順で再作成
4. `status: "reserved"` のメッセージは `status: "draft"` で作成し、確認後に手動で公開

> ⚠️ 復元時は新しいIDが割り振られます（元のIDとは異なる）。  
> 外部リンク・フォーム連携・URLアクションがIDに依存している場合は手動で再設定が必要です。  
> アクション（`action_id`）はAPI作成不可のため、管理画面で再作成後にIDを差し替えてください。
