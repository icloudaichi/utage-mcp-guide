# UTAGE AI Skill - フィードバック報告

エラー・新発見・改善提案を GitHub Discussions に投稿します。

---

## 使い方（AIへの指示）

```
「[エラー内容] をGitHubに報告しといて」
「[この仕様] をdiscussionに上げておいて」
```

AIが以下を自動実行します:
1. エラー内容を整理（タイトル・本文を自動生成）
2. `report_discussion.py` を実行
3. GitHub Discussions に投稿
4. 投稿URLを返す

> ⚠️ `report_discussion.py` は `GITHUB_TOKEN` が必要です。MCPのみでセットアップした場合は `.env` に `GITHUB_TOKEN` を追加するか、下記の手動投稿をご利用ください。

---

## 手動投稿

GitHub Token を持っていない場合は直接投稿:
https://github.com/icloudaichi/utage-mcp-guide/discussions/new

カテゴリ:
- `Bug` → APIの動作が仕様と異なる
- `Ideas` → SKILL.mdに追加すべき知見
- `Q&A` → 動作不明・要検証

---

## report_discussion.py 使い方

```bash
export GITHUB_TOKEN="your_token_here"
python3 report/report_discussion.py \
  --title "image_srcで画像が保存されない" \
  --body "image要素にimage_srcを使ったが保存されなかった。image_urlが正しい。" \
  --category Bug
```
