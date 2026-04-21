# UTAGE AI Skill - セットアップ

初回利用時に実行してください。

---

## Step 1: .env を作成

```bash
cp .env.example .env
```

`.env` を開いて以下を設定:

- `UTAGE_API_KEY`: UTAGE管理画面 > API設定 から取得
- `GITHUB_TOKEN`: https://github.com/settings/tokens から取得（任意）
  - 必要スコープ: `repo`

---

## Step 2: UTAGE API疎通確認

```bash
source .env
curl -s "https://api.utage-system.com/v1/funnels" \
  -H "Authorization: Bearer $UTAGE_API_KEY" | head -c 200
```

レスポンスが返ればOKです。

---

## Step 3: MCPサーバー設定 または REST API直接利用

このスキルは **2つの動作モード** があります。

| モード | 対応ツール | 認証方法 |
|:---|:---|:---|
| **MCP接続** | Claude Code / claude.ai | OAuth（ブラウザ認証） |
| **MCP接続** | **VS Codeフォーク系IDE**（Cursor・Antigravity等） | **mcp-remote経由でOAuth** ✅推奨 |
| **REST API直接** | 全ツール共通（MCP不要） | UTAGE_API_KEY（.env） |

> 💡 MCPサーバーに接続することで新規ツールの追加を自動検知できるため、MCP接続を強く推奨します。  
> ⚠️ OAuthトークンには有効期限があります。切れた場合は再認証が必要です。

---

### モードA: MCP接続

UTAGEのMCPサーバーURL:
```
https://api.utage-system.com/mcp
```

**Claude Code（`.mcp.json`）**:
```json
{
  "mcpServers": {
    "utage-api": {
      "url": "https://api.utage-system.com/mcp"
    }
  }
}
```

**claude.ai（ブラウザ版）**:
1. 画面左下 **カスタマイズ** → **コネクター** → **+** → **カスタムコネクターを追加**
2. URL に `https://api.utage-system.com/mcp` を入力
3. UTAGEのログイン/認可画面で認証

---

**VS Codeフォーク系IDE（Cursor・Antigravity・Windsurf等）**:

VS Codeフォーク系IDEはネイティブのOAuthブラウザフローをサポートしていないため、`mcp-remote` をローカルプロキシとして使用します。`mcp-remote` が初回接続時にブラウザでUTAGEのOAuth認証を開きます。

**前提**: Node.js（npx）がインストール済みであること

**Cursor**: `~/.cursor/mcp.json`  
**Antigravity**: `~/.gemini/antigravity/mcp_config.json`  
**Windsurf**: `~/.codeium/windsurf/mcp_config.json`  

```json
{
  "mcpServers": {
    "utage-api": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://api.utage-system.com/mcp"
      ]
    }
  }
}
```

設定後にIDEを再起動すると、初回のみブラウザでUTAGEのOAuth認証画面が開きます。認証完了後は自動的にトークンがキャッシュされます。

> ⚠️ 設定後はIDEを再起動すること  
> ⚠️ `mcp-remote` が動作するにはNode.js（v18以上）が必要

---

### モードB: REST API直接利用（全ツール共通・MCP不要）

`.env` に `UTAGE_API_KEY` を設定するだけで使えます。  
MCP接続の有無に関わらず、すべての操作がREST APIで代替可能です。

```bash
# 動作確認
source .env
curl -s "https://api.utage-system.com/v1/funnels" \
  -H "Authorization: Bearer $UTAGE_API_KEY" | python3 -m json.tool | head -20
```

レスポンスが返ればセットアップ完了です。

---

## Step 4: 動作確認

ルートの SKILL.md を読み込んで「UTAGEのファネル一覧を取得して」と指示してみてください。
