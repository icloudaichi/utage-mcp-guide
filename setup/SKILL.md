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

[公式セットアップ](https://docs.utage-system.com/mcp/setup)ではCursorはURLとAPIキーの直接接続、OAuth対応クライアントはURL登録を案内しています。以下は `mcp-remote` 経由で既存OAuth接続を使う代替例です。全IDEが同じ認証方式だと判断せず、現在のクライアント手順を確認してください。この方式を選ぶ場合は `npx` がパッケージを取得することがあります。

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

> 「UTAGE MCPの `find_tools` を呼んで、カテゴリ別のツール一覧を見せて」

2026-10-03のLBS接続では253件のメタデータを確認しました（`find_tools` 自体は除外）。[全一覧](../docs/tool-catalog.md)にカテゴリとpreview状態を記録しています。名前・説明の発見と、クライアントの入力スキーマ確認、実read成功を区別してください。

`find_tools` の実質的な絞り込みは `category` だけです。`query` はやりたいことのメモとして受け付けられますが、現在は結果の絞り込みには使われません。

続けて読み取り系ツールを確認します:

> 「UTAGEのファネル一覧を取得して」

ファネル一覧が返ればセットアップ完了です。

必要なツールが見えない場合は接続URL・対象アカウントとクライアントのツール定義を確認してください。認証キャッシュ削除・再認証を自動実行せず、取得できない範囲を記録します。`/mcp/<識別子>` は接続ラベルであり、対象は認証時のログインにより決まります。

- preview `message_*` ツール
- preview `member_*` ツール
- preview `event_*` ツール
- `funnel_action_*` ツール
- `funnel_stats_get` / `funnel_stats_daily` / `funnel_subscriber_list`
- `media_upload_url` / `media_video_upload_url` / `media_audio_upload_url`
- `media_complete` / `media_video_complete` / `media_audio_complete`
- `element_types_mail` / `element_types_mail_properties`
- `element_types_lesson` / `element_types_lesson_properties`

---

## トラブルシューティング

### トークン失効時の再認証

認証エラーはblocked authとして記録します。ユーザーが再認証を依頼した場合に限り、対象接続のクライアント手順で復旧します。全サーバー共通のキャッシュを削除する方法は、他の接続へ影響するため使いません。

### TLS証明書エラー（UNABLE_TO_GET_ISSUER_CERT_LOCALLY）

`mcp-remote` 起動時にブラウザのOAuth認証が始まらず、以下のエラーが出る場合があります:

```
TypeError: fetch failed
cause: Error: unable to get local issuer certificate
```

**原因**: Node.js がシステムのCA証明書ストアを参照できない環境（企業プロキシ、VPN等）で発生します。

クライアント・Node.jsの証明書設定と信頼するCAを確認し、TLS検証を維持してください。追加CAが必要な環境では `NODE_EXTRA_CA_CERTS` に信頼済みPEMファイルのパスを設定します。PEM本文を環境変数へ入れる方式やTLS検証無効化を使わず、復旧できない場合は接続未検証として報告します。

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
