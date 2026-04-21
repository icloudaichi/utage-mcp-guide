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

| カテゴリ | 参照先 | MCPツール例 |
|:---|:---|:---|
| ステップメール・LINE配信 | `messages/SKILL.md` | `message_create`, `message_update` |
| ファネル・LP・ページ要素 | `funnels/SKILL.md` | `funnel_page_create`, `element_types_funnel` |
| シナリオ管理 | `scenarios/SKILL.md` | `message_scenario_create` |
| 配信アカウント・ラベル・読者 | `accounts/SKILL.md` | `message_account_list`, `message_label_create` |
| メディア参照 | `media/SKILL.md` | `media_video_list` |
| エラー報告・フィードバック | `report/SKILL.md` | `report_discussion.py` |

---

## ⚠️ 全カテゴリ共通の既知トラップ

> 実機検証で発見したエラー一覧です。AIはこれを参照してから操作してください。

### メッセージAPI

| # | 症状 | 原因 | 正解 |
|:---|:---|:---|:---|
| 1 | `validation_error: 送信タイプは必ず指定してください` | `send_type` を省略 | `send_type: "scheduled"` or `"immediately"` を必ず付ける |
| 2 | 即時配信のステップが公開できない | `send_type: "immediately"` はAPI経由で公開不可 | 管理画面から手動公開 or `send_date: 0` で代替 |

### ファネル要素 — プロパティ名の誤記

| # | 要素 | ❌ 使えない | ✅ 正しい | 症状 |
|:---|:---|:---|:---|:---|
| 3 | `image` | `image_src` | **`image_url`** | エラーなし・サイレント失敗 |
| 4 | `video` | `video_id` | **`video_url`（絶対パスURL）** | 保存されない |
| 5 | `table` | `content` | **`body_rows` + `body_cols` + `table_data`** | キーが存在しない |
| 6 | `deadline` | `target_datetime` | **`target_type`（必須）+ `target_date`** | 受け付けられない |
| 7 | `accordion` | `title` | **`content`（ヘッダー）+ `sub_content`** | サイレント失敗 |
| 8 | `form-button` | `button_text` / `button_text_color` | **`content` / `color`** | サイレント失敗 |

### ページAPI

| # | 症状 | 原因 | 対策 |
|:---|:---|:---|:---|
| 9 | PUT後に他の要素がnullリセット | 変更箇所だけ送った | PUT前に必ずGETして全フィールド含めて送信 |
| 10 | `padding_top/bottom` が効かない | `section` に設定した | **`col`** に設定する |
| 11 | 日本語JSONでエンコードエラー | パイプで渡した | `--data-binary @file` でファイル経由 |

### API制限

| # | 操作 | 結果 |
|:---|:---|:---|
| 12 | `POST /actions` アクション作成 | **405 Method Not Allowed**（管理画面のみ） |
| 13 | シナリオ作成で `name` フィールド | **フィールド名は `title`** が正しい |

---

## このスキルについて

- **ライセンス**: MIT（スクリプト）/ CC BY 4.0（ドキュメント）
- **対象**: UTAGE 公式 MCPサーバー + REST API v1
- **メンテナー**: [@icloudaichi](https://github.com/icloudaichi)
- **バージョン**: 0.2.0（2026-04-21）
- **フィードバック**: [GitHub Discussions](https://github.com/icloudaichi/utage-mcp-guide/discussions)
