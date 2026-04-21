# utage-mcp-guide

UTAGEのMCPサーバーを最大限活用するためのオンボーディングキット。  
実機検証で発見した落とし穴を回避し、AIでUTAGE操作を安全に自動化します。

## 思想

> 「MCPサーバーに接続すればツール定義は手に入る。  
> しかしサイレント失敗やプロパティ名の罠は、踏んだ人にしかわからない。」  
> 「その知見を集めて、全員が同じ穴に落ちないようにするプロジェクト。」

## 特徴

- **MCPファースト**: MCPサーバーに接続するだけで全操作が可能（APIキー設定不要）
- **実機検証済みの落とし穴13件**を記録（公式ドキュメントの誤記・サイレント失敗を含む）
- MDファイルからステップメールを一括投入するワークフローを収録
- エラー発見時は GitHub Discussions に自動報告

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
utage-mcp-guide の SKILL.md を読んで、[やりたいこと] をやって
```

## フォルダ構成

```
utage-mcp-guide/
├── SKILL.md          # エントリーポイント（共通トラップ集）
├── messages/         # ステップメール・LINE配信
├── funnels/          # ファネル・LP・ページ要素
├── scenarios/        # シナリオ管理
├── accounts/         # 配信アカウント・ラベル・読者
├── media/            # メディア参照
├── report/           # GitHub Discussionsへのフィードバック投稿
└── setup/            # 初回セットアップ
```

## フィードバック

エラー・新発見・改善提案は [GitHub Discussions](https://github.com/icloudaichi/utage-mcp-guide/discussions) へ。  
AIに「GitHubに報告して」と言えば `report_discussion.py` が自動投稿します。

## ライセンス

- スクリプト（.py）: MIT License
- ドキュメント（SKILL.md, README.md 等）: CC BY 4.0

公開情報（UTAGE公式APIドキュメント・MCP仕様）をもとに実機検証した知見をシェアしています。

## メンテナー

[@icloudaichi](https://github.com/icloudaichi)
