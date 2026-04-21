# UTAGE MCP Guide - セットアップ

VS Codeフォーク系IDE（Cursor・Antigravity・Windsurf等）でUTAGE MCPサーバーに接続するためのガイドです。

> **Claude（Claude Code / claude.ai）をお使いの方へ**  
> Claudeは公式でUTAGE MCPに対応しています。  
> → 公式ドキュメント: [docs.utage-system.com](https://docs.utage-system.com)  
> このガイドの落とし穴集（ルートの SKILL.md）は Claude でもそのまま活用できます。

---

## 前提条件

| 必要なもの | バージョン | 確認方法 |
|:---|:---|:---|
| **Node.js** | v18 以上 | `node -v` |
| **npx** | Node.js に同梱 | `npx -v` |

Node.js が未インストールの場合:

```bash
# macOS（Homebrew）
brew install node

# または公式サイトからインストール
# https://nodejs.org/
```

> `mcp-remote` は npx 経由で自動インストールされるため、個別のインストールは不要です。

---

## Step 1: MCPサーバーを設定する

VS Codeフォーク系IDEはOAuthブラウザフローを直接サポートしないため、`mcp-remote` をプロキシとして使用します。

使用するIDEに合わせて、以下の設定ファイルに追記してください。

| IDE | 設定ファイル |
|:---|:---|
| Cursor | `~/.cursor/mcp.json` |
| Antigravity | `~/.gemini/antigravity/mcp_config.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |

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

設定後にIDEを再起動すると、**初回のみブラウザでUTAGEのOAuth認証画面が開きます**。  
認証完了後はトークンが自動キャッシュされ、次回以降は再認証不要です。

---

## Step 2: 動作確認

IDEを再起動後、AIに以下のように指示してみてください：

> 「UTAGEのファネル一覧を取得して」

ファネル一覧が返ればセットアップ完了です。

---

## トラブルシューティング

### トークン失効時の再認証

認証エラーが発生した場合は以下を実行してからIDEを再起動してください：

```bash
rm -rf ~/.mcp-auth/
```

### TLS証明書エラー（UNABLE_TO_GET_ISSUER_CERT_LOCALLY）

`mcp-remote` 起動時にブラウザのOAuth認証が始まらず、以下のエラーが出る場合があります:

```
TypeError: fetch failed
cause: Error: unable to get local issuer certificate
```

**原因**: Node.js がシステムのCA証明書ストアを参照できない環境（企業プロキシ、VPN等）で発生します。

**暫定対処（開発環境限定）**:

MCP設定に環境変数を追加してTLS検証をスキップします：

```json
{
  "mcpServers": {
    "utage-api": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://api.utage-system.com/mcp"],
      "env": {
        "NODE_TLS_REJECT_UNAUTHORIZED": "0"
      }
    }
  }
}
```

> ⚠️ `NODE_TLS_REJECT_UNAUTHORIZED=0` はTLS証明書の検証を無効化します。**本番環境やセキュリティが重要な環境では使用しないでください**。  
> この問題は mcp-remote 側の既知の課題として報告中です。

**恒久対処**: Node.js にシステムのCA証明書を認識させます：

```bash
# macOSの場合
export NODE_EXTRA_CA_CERTS="$(security find-certificate -a -p /System/Library/Keychains/SystemRootCertificates.keychain)"
```

---

## 補足: REST API直接利用（任意）

MCPを使わずREST APIで直接操作したい場合は、`.env` に `UTAGE_API_KEY` を設定します。

```bash
cp .env.example .env
# .env を開いて UTAGE_API_KEY を設定
```

```bash
# 疎通確認
source .env
curl -s "https://api.utage-system.com/v1/funnels" \
  -H "Authorization: Bearer $UTAGE_API_KEY" | python3 -m json.tool | head -20
```
