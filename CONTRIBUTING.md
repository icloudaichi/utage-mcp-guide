# コントリビューションガイド

## フィードバックの送り方

### AIに任せる（推奨）

AIに「GitHubに報告して」と言うだけでOKです。

```
「image_urlで画像が表示されなかった。GitHubに報告して」
→ report/report_discussion.py が自動実行されてDiscussionsに投稿されます
```

### 直接投稿する

https://github.com/icloudaichi/utage-mcp-guide/discussions/new

カテゴリの目安:
- **Bug**: APIが仕様と異なる動作をする
- **Ideas**: SKILL.mdに追加すべき知見がある
- **Q&A**: 動作が不明・要検証

## スキルファイルの更新提案

SKILL.mdの内容を修正・追加したい場合:

1. このリポジトリをFork
2. 変更をコミット
3. Pull Requestを送る

API/MCPの更新では、参照元と確認日、metadata発見・schema確認・実read・mockを分けて記録してください。`python3 -m unittest discover -s tests -v` でoffline検証を実行できます。疎通確認でcreate/update/delete/send・実決済・権限変更を実行せず、未知のendpointを推測しません。公開証跡は値を除去した型構造と固定字段receiptに限定し、認証情報・会員PII・決済ID・本文をアップロードしません。

## ライセンス

コントリビューションはMIT（スクリプト）/ CC BY 4.0（ドキュメント）に同意したものとみなします。
