# utage-skill

UTAGEをAI（MCP + REST API）で操作するための、実機検証済みオープンスキルです。

## 思想

> 「パソコン上の操作ナレッジは、AIに代替されるぐらいなら今すぐAIに渡して進化させた方がいい。」  
> 「一人でやるのは非効率だから、一緒に育てていきましょう。」

UTAGEのAPI操作知識をオープンソースとして公開し、コミュニティで育てていくプロジェクトです。

## 特徴

- UTAGE 公式 MCP + REST API v1 のみ使用（スクレイピング不使用）
- **実機検証済みの落とし穴15件**を記録（公式ドキュメントの誤記を含む）
- MDファイルからステップメールを一括投入するワークフローを収録
- エラー発見時は `report_discussion.py` でGitHub Discussionsに自動報告

## セットアップ

MCPサーバーに接続するだけで使えます。APIキー設定は不要です。

```json
// Cursor: ~/.cursor/mcp.json
// Antigravity: ~/.gemini/antigravity/mcp_config.json
// Windsurf: ~/.codeium/windsurf/mcp_config.json
{
  "mcpServers": {
    "utage-api": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://api.utage-system.com/mcp"]
    }
  }
}
```

IDEを再起動すると初回のみブラウザでOAuth認証が開きます。

→ 詳細・IDE別設定は `setup/SKILL.md` を参照

## 使い方

AIツール（Antigravity / Cursor / Claude Code 等）に以下のように伝えてください:

```
utage-skill の SKILL.md を読んで、[やりたいこと] をやって
```

## フォルダ構成

```
utage-skill/
├── SKILL.md          # エントリーポイント（共通設定・落とし穴一覧）
├── messages/         # ステップメール・LINE配信
├── funnels/          # ファネル・LP・ページ要素
├── scenarios/        # シナリオ管理
├── accounts/         # 配信アカウント
├── media/            # メディア参照
├── report/           # GitHub Discussionsへのフィードバック投稿
└── setup/            # 初回セットアップ
```

## フィードバック

エラー・新発見・改善提案は [GitHub Discussions](https://github.com/icloudaichi/utage-skill/discussions) へ。  
AIに「GitHubに報告して」と言えば `report_discussion.py` が自動投稿します。

## ライセンス

- スクリプト（.py）: MIT License
- ドキュメント（SKILL.md, README.md 等）: CC BY 4.0

公開情報（UTAGE公式APIドキュメント・MCP仕様）をもとに実機検証した知見をシェアしています。

## メンテナー

[@icloudaichi](https://github.com/icloudaichi)
