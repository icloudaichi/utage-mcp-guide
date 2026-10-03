# UTAGE AI Skill - payment

商品と価格ラインナップを扱うpreviewカテゴリです。2026-10-03のLBS `find_tools` メタデータに17ツールが露出しました。入力スキーマはこの記録に含まれません。実行クライアントの定義を確認してください。

| read | 用途 |
|---|---|
| `payment_product_list` / `payment_product_get` | 商品設定一覧・詳細 |
| `payment_product_group_list` / `payment_product_group_get` | 商品グループ一覧・詳細 |
| `payment_product_detail_list` / `payment_product_detail_get` | 価格ラインナップ一覧・全設定 |

| write（検証で実行しない） | 用途 |
|---|---|
| `payment_product_create/update/delete/reorder` | 商品作成・更新・削除・並び替え |
| `payment_product_group_create/update/delete` | 商品グループ変更 |
| `payment_product_detail_create/update/delete/reorder` | 価格ラインナップ変更 |

商品一覧と価格ラインナップ一覧は同日の少量read証跡で確認しました。価格ラインナップ詳細も `detail_id` を使用したreadで成功しました。`product_detail_id` を指定した試行は `-32602` で失敗しました。これは呼出し引数の観測で、JSON Schema全体は未取得です。timeout/非JSON応答の試行は成功へ上書きしません。外側のproxy `success` だけで、非JSON文字列・下位errorを成功扱いしません。

これは商品plan設定です。支払方法、決済代行会社、課金方式、金額や周期を確認できても、購入者ごとの契約status、次回課金、subscription IDを確認したことにはなりません。個別契約のツールは今回未露出です。架空のREST endpointや契約IDを作り、推測でアクセスしないでください。

公開fixtureには金額・商品ID・決済ID・通知先・本文を残さず型構造だけを保存します。[検証行列と限界](../docs/endpoint-testing.md)、[全253件一覧](../docs/tool-catalog.md)を参照してください。
