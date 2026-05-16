# UTAGE AI Skill - accounts

配信アカウント・ラベル・読者データを管理します。

## MCPツール

| ツール名 | 操作 |
|:---|:---|
| `message_account_list` / `message_account_create` | アカウントCRUD |
| `message_label_list` / `message_label_create` / `message_label_get` | ラベル取得・作成 |
| `message_label_update` / `message_label_delete` | ラベル更新・削除 |
| `message_common_reader_label_list` / `_create` / `_delete` | 読者へのラベル付与・削除 |
| `message_reader_list_all` / `message_reader_list` / `message_reader_get` | 読者データ参照 |
| `message_condition_types` | 読者絞り込みに使える条件キー・演算子の確認 |
| `message_placeholder_list` | シナリオ別に絞り込み可能な読者項目の確認 |

---

## アカウントタイプ

| type | 用途 |
|:---|:---|
| `mail` | メールのみ |
| `line` | LINEのみ |
| `mail_line` | メール + LINE 統合 |

---

## ⚠️ 注意点

> → 全カテゴリ共通トラップはルートの SKILL.md を参照

- 読者データの更新（メール変更等）は API 非対応。管理画面のみ
- `message_reader_list_all` の条件キーは横断取得用に制限されます。シナリオ固有の読者項目で絞る場合は `message_reader_list` を使うこと
- 読者項目で絞る前に `message_placeholder_list` の `is_filterable=true` を確認すること
- REST/MCPの読者レスポンスでは `mail` / `name` が `null` になる場合があります。メールアドレス等のPII確認は管理画面CSVダウンロードが必要
- REST `conditions` は `[{"rules":[...]}]` の配列形式。`{"rules":[...]}` は422

---

## 補足: REST API（curl）

```bash
# アカウント一覧
curl -s "https://api.utage-system.com/v1/accounts" \
  -H "Authorization: Bearer $UTAGE_API_KEY"

# ラベル一覧
curl -s "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/labels" \
  -H "Authorization: Bearer $UTAGE_API_KEY"

# ラベル作成
curl -s -X POST "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/labels" \
  -H "Authorization: Bearer $UTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "テストラベル"}'

# ラベル詳細
curl -s "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/labels/LABEL_ID" \
  -H "Authorization: Bearer $UTAGE_API_KEY"

# ラベル更新
curl -s -X PUT "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/labels/LABEL_ID" \
  -H "Authorization: Bearer $UTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "更新後ラベル名"}'

# ラベル削除
curl -s -X DELETE "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/labels/LABEL_ID" \
  -H "Authorization: Bearer $UTAGE_API_KEY"

# 読者一覧
curl -s "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/readers" \
  -H "Authorization: Bearer $UTAGE_API_KEY"

# シナリオ別読者一覧
curl -s "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/scenarios/SCENARIO_ID/readers" \
  -H "Authorization: Bearer $UTAGE_API_KEY"

# 読者条件検索（conditions は配列形式）
curl -sG "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/scenarios/SCENARIO_ID/readers" \
  -H "Authorization: Bearer $UTAGE_API_KEY" \
  --data-urlencode 'conditions=[{"rules":[{"key":"mail","condition":"including","value":"example.com"}]}]'
```

2026-05-16 実操作確認:
- MCP `message_label_create` / `message_label_list` 成功
- REST `POST /accounts/{account_id}/labels` / `GET /accounts/{account_id}/labels` / `GET /accounts/{account_id}/labels/{label_id}` / `PUT /accounts/{account_id}/labels/{label_id}` / `DELETE /accounts/{account_id}/labels/{label_id}` 成功
- `message_reader_list` の `conditions` は `message_condition_types` と `message_placeholder_list.is_filterable` を確認してから使う
- フォーム登録読者はREST/MCPで `mail/name=null` になる場合があるが、`mail` 条件検索には一致。CSVダウンロードではメールアドレス・登録元IP・ステータスまで取得できる
- `message_common_reader_label_create` → `message_reader_list(label condition)` → `message_common_reader_label_delete` 成功
