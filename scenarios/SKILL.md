# UTAGE AI Skill - scenarios

配信アカウント配下のシナリオを管理します。

## MCPツール

| ツール名 | 操作 |
|:---|:---|
| `message_scenario_list` | シナリオ一覧取得（title で検索可） |
| `message_scenario_create` | シナリオ作成 |

---

## ⚠️ 注意点

> → 全カテゴリ共通トラップはルートの SKILL.md を参照

- **フィールド名は `title`**（`name` ではない）。`name` を使うとエラーなく成功するが、タイトルが空になるサイレント失敗

| パラメータ | 必須 | 説明 |
|:---|:---|:---|
| `account_id` | ✅ | 配信アカウントID |
| `title` | ✅ | シナリオタイトル（`name` は NG） |
| `open_title` | - | 公開タイトル（読者に見える名前） |

---

## 実践フロー

1. `message_scenario_create` でシナリオ作成
2. 返された `scenario_id` で `message_create` でメッセージ一括投入
→ `messages/SKILL.md` を参照

---

## 補足: REST API（curl）

```bash
# 一覧取得
curl -s "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/scenarios" \
  -H "Authorization: Bearer $UTAGE_API_KEY"

# 作成
curl -s -X POST "https://api.utage-system.com/v1/accounts/ACCOUNT_ID/scenarios" \
  -H "Authorization: Bearer $UTAGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title": "プロモーションシナリオ"}'
```

2026-05-16 実操作確認:
- MCP `message_scenario_create` 成功
- REST `POST /accounts/{account_id}/scenarios` / `GET /accounts/{account_id}/scenarios` 成功
