# エンドポイント検証と確認範囲（2026-10-03）

[現行253ツール一覧](tool-catalog.md)と[機械可読カタログ](evidence/tool-catalog-2026-10-03.json)には、read/write分類、previewなどの提供状態、今回の実read、未実行、確認済みREST対応を記録しています。提供状態はLBSの1接続で取得したメタデータです。他接続への提供や動作を保証しません。RESTパスは確認できたものだけを掲載し、MCPツール名から推測しません。

## 根拠と仕様

公式[API概要](https://docs.utage-system.com/api-reference/overview)のベースは `https://api.utage-system.com/v1`。更新は `PATCH` が正規メソッドで、既存の `PUT` は後方互換です。公式[認証](https://docs.utage-system.com/authentication)はBearer APIキーを使用します。参照系のうち同ページに列挙された6エンドポイントは認証不要です。今回APIキーを発行していません。

公式[セットアップ](https://docs.utage-system.com/mcp/setup)は、クライアントによってOAuthまたはAPIキーの接続方法を案内しています。`/mcp/<識別子>` は接続を分けるラベルです。対象アカウントはそのURLで認証したアカウントにより決まるため、URLの末尾だけで確認を済ませず、小さいreadで対象を照合します。

[現行MCP仕様](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)では `tools/list` が入力スキーマ、任意の出力スキーマやannotationsを返します。今回のUTAGE `find_tools` 結果は名前・説明・カテゴリ・preview状態だけでした。**`find_tools` は `tools/list` 全件やJSON Schemaの取得証拠ではありません**。入力/出力スキーマと `readOnlyHint` は未取得です。実行するクライアントのツール定義を別途確認してください。HTTP POSTでMCPやread proxyを呼ぶことと、業務リソースを更新することは別の分類です。ローカルallowlistもreadの意味を明示した代表ツールだけに限定しています。

## テスト行列

| 対象 | 実read | offline契約 | 判定・限界 |
|---|---|---|---|
| `GET /v1/element-types/funnel` | 本タスクで1回、HTTP 200 | 応答・値除去 | 認証不要の参照。業務アカウント疎通の証拠にはしない |
| `element_types_funnel` | 既存LBS OAuth proxyで1回、HTTP 200 | MCP/JSON-RPC/proxy unwrap | 型構造だけfixtureへ保存 |
| `message_account_list` | 同日共有LBS/Wasa証跡を再利用 | profile分離・error判定 | LBS 7行、Wasa 25行。全件取得を主張しない |
| 同ツール、hirahara（Daichi接続） | 共有証跡でauth error | 認証エラー分類 | blocked auth。再認証・別接続fallbackなし |
| `message_reader_list` | 共有の1行readを再利用 | page/meta・日時の分離 | 少量の形確認。全読者を取得していない |
| `payment_product_list` | 共有read、21行 | 値除去・一覧のshape | 商品設定。個別の購入・契約状態ではない |
| `payment_product_detail_list` | 共有read 2例 | 型構造fixture | `payment_provider`、`charge_type`、`billing_cycle`、`amount`、`recurring_amount` を確認。値は公開しない |
| `payment_product_detail_get` | 誤引数の失敗後、`detail_id` で共有read成功 | `-32602`回帰・型構造fixture | `product_detail_id` は誤り。timeout/非JSON応答は失敗のまま別記録 |
| その他read | 今回未実行 | 代表契約のみ | 8月以前の確認を今回の成功として転記しない |
| catalogの133 write | 実呼出し0 | 代表read planが全133件を拒否 | create/update/delete/send、既読化、upload URL発行/完了通知などを含む |
| subscription cancel/実決済 | 実呼出し0 | 未知ツールも拒否するmock | 個別契約read/write endpointは今回未確認。存在を推測して呼ばない |

`payment_*` の17件は商品と価格ラインナップの設定です。個別契約status、次回課金日、決済代行のsubscription IDを返すツールは今回の名前・説明一覧では未露出でした。商品設定の継続金額と周期から個別の次回課金日を算出しません。`message_reader_activity_list` も今回未露出です。`member_student_activity_log_list` は別リソースで、代替とはみなしません。

## pagination・日時・エラー

公式API概要は `page` と `per_page`、応答 `meta.current_page/per_page/total` を記載しています。ページング対象のローカル検証では途中ページ欠落、重複ID、total変化、空の途中ページ、boolを含む不正metaを拒否し、連続した全件が確認できたときだけcompleteとします。ページング対象でmetaを返さない一覧から全件完了を推定しません。公式[ステップ一覧](https://docs.utage-system.com/api-reference/funnel/step-list)・[ページ一覧](https://docs.utage-system.com/api-reference/funnel/page-list)は `data` のみの非ページング形式なので、back up scriptはそのendpoint固有の形とIDを検査して受理します。この分岐はmockで確認し、実backupは未実行です。MCP `tools/list` のcursorとUTAGEデータ一覧のpageを混同しません。

公式[読者一覧](https://docs.utage-system.com/api-reference/message/reader/list)と[ファネル登録者一覧](https://docs.utage-system.com/api-reference/funnel/subscriber-list)には `created_at` があり、後者の登録日フィルタはこれを基準にします。確認した公開資料には `submitted_at` とtimezoneの保証がありません。読者作成日時をフォーム再送信日時として使用せず、offsetのない日時はprovider naiveとして保持します。JST/UTCの推定変換、期日判定には使いません。

公式[エラー処理](https://docs.utage-system.com/guides/error-handling)を参照し、400/401/403/404/409/422やMCP `isError`、JSON-RPC `error`、下位provider `error`、proxyのprofile/tool不一致を成功扱いしません。429の待機はproviderのreset指示に従い、この検証ではリトライしていません。生のerror本文は機密を含む可能性があるためfixtureに保存しません。

## 実行方法

Python標準ライブラリのみで、ネットワークやcredentialなしで動く契約テストです。

```bash
python3 -m unittest discover -s tests -v
```

`tests/fixtures/*-shape.json` は実応答から値を落とした型構造です。mockのレスポンスはテスト内に明示しています。**offlineテスト成功はサービスのschema適合・本番write成功を意味しません**。live runnerを配布せず、既存認証の小代表readで得た[receipt](evidence/read-receipts-2026-10-03.json)を参照します。receiptには入力ID、token、cookie、会員情報、金額、決済ID、メール本文を含めません。

新runtime/install/OAuth/key/有料APIは0件。既存個人skillsや他リポジトリは変更していません。バックアップの実サービス実行もしていません。
