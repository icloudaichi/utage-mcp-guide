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

| モード | 対応確認済みツール | 認証方法 |
|:---|:---|:---|
| **MCP接続** | Claude Code / claude.ai | OAuth（ブラウザ認証） |
| **MCP接続** | **Cursor** | **APIキー（Bearer、.cursor/mcp.json）** |
| **MCP接続** | **Antigravity** | **APIキー（Bearer、mcp_config.json）** |
| **REST API直接** | 全ツール共通（MCP不要） | UTAGE_API_KEY（.env） |

> ⚠️ **Cursor / Antigravity**: OAuthフローが不安定なため、**APIキー（Bearer）方式を推奨**。  
> MCPサーバーに接続しないと新規ツールの追加を自動検知できないため、MCP接続の設定を強く推奨します。

---

### モードA: MCP接続

UTAGEのMCPサーバーURL:
```
https://api.utage-system.com/mcp
```

初回接続時にブラウザでUTAGEのOAuth認証（ログイン＋認可）が必要です。  
認証が完了すると UTAGE管理画面 > API設定 に「〇〇 MCP接続」としてキーが作成されます。

> ⚠️ OAuthトークンには有効期限があります。接続が切れた場合は再認証が必要です。

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

**Cursor**:  
OAuthフローが不安定なため、APIキーをBearerトークンとして設定します。

設定ファイルのパス（グローバル設定）:
```
~/.cursor/mcp.json
```

設定内容（`YOUR_API_KEY` を実際のキーに置き換え）:
```json
{
  "mcpServers": {
    "utage-api": {
      "url": "https://api.utage-system.com/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

> ⚠️ 設定後はCursorを再起動すること  
> ⚠️ OAuthフローで認証できた場合はそちらでも可（ただしトークン有効期限に注意）

---

**Antigravity（Gemini CLI）**:  
APIキーをBearerトークンとして `mcp_config.json` に直接記載します。

設定ファイルのパス:
```
~/.gemini/antigravity/mcp_config.json
```

設定内容（`YOUR_API_KEY` を実際のキーに置き換え）:
```json
{
  "mcpServers": {
    "utage-api": {
      "serverUrl": "https://api.utage-system.com/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

> ⚠️ キー名は `httpUrl` や `url` ではなく **`serverUrl`** を使用すること（Antigravity固有の仕様）  
> ⚠️ `settings.json` の `mcpServers` セクションではなく `mcp_config.json` に記載すること  
> ⚠️ 設定後はAntigravityセッションを再起動すること  
> 💡 OAuthフローで認証が開けるケースもあるが、トークン有効期限の問題があるためAPIキー方式を推奨

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
