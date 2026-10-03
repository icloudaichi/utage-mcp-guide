# MAGI 修正版の相互批判 — CASPAR

- 対象: revision `497bacc46b7ca412e9fc0959ff37462720e772d6` / 固定 `private/review-revision`。
- 確認時刻: 2026-10-03 07:34 UTC。
- 入力: `private/magi-balthasar-revision.md` を全文読了し、R1 を独立再現。
- 実通信・credential アクセス 0。repo コード編集 0。Python 標準ライブラリと temporary directory の合成 fixture のみ。

## 判定と初回承認との関係

**changes_requested — BALTHASAR R1 / P2 を支持。** 先の CASPAR 独立再レビューは、初回指摘の修正と現在の fixture の型構造に対する approved として履歴に残す。今回追加された反例により、同じ pinned revision の fixture 継続運用 guard について P2 を補足する。現行 fixture の機密漏洩や P0/P1 の新障害を検出した判断ではない。

## ❌ R1 / P2 の独立再現

位置: `tests/test_catalog_snapshot.py:83-84`。関連 `:69-80,88-92`。

実際の `CatalogSnapshotTests.test_fixtures_are_only_anonymous_shape_not_response_values` を import し、temporary directory に合成 `tests/fixtures/synthetic-shape.json` を作成して module の `ROOT` だけを mock した。検査関数のコピーや別 validator を使わず、動的 key 拒否回帰も含めた現行 test method をそのまま実行した。

全 fixture は `origin=observed_types_only` / `case=synthetic` / `tool=payment_product_detail_get`。結果:

| 合成 shape | 現行 guard | 適切な結果 |
|---|---|---|
| `{object:{amount:123456,id:9281}}` | pass | fail（業務の生数値） |
| `{object:{id:true,amount:false}}` | pass | fail（生 bool。Python の bool は int の subclass） |
| `{array:[123456],length:1}` | pass | fail（array の生数値） |
| `{object:{length:123456}}` | pass | fail（名称が length でも業務 field 内） |
| `{array:[],length:true}` | pass | fail（構造値の型違い） |
| `{array:[],length:-1}` | pass | fail（構造値の範囲違い） |
| 型タグ object + array length 1 + `[other-fields]` count 2/types | pass | pass（正当な匿名構造） |

`assertIsInstance(value,int)` がすべての位置で使われるため、整数が長さなのか金額・IDなのかを区別できない。schema key を固定化した改善は有効だが、それだけでは生の数値値を排除できない。

## 優先度・影響範囲

P2 を支持する。検査が公開 fixture の「値を落とした型構造だけ」という運用契約を掲げながら、raw 金額・数値 ID を通す反例がある。今後の更新担当者がこの test pass を公開 gate として使用すると、数値情報の混入を見逃し得る。

P1 へ上げない理由: 現行 fixture の漏洩は検出していない。generator の scalar 値除去と別 private scan が存在し、通常の unwrap/receipt や実サービス read が直接この反例で誤動作するわけではない。この guard の継続運用上の不足として P2 が適切。

現在の public fixture の数値 scalar は `length` と `count` の構造位置にある。数値 leaf の位置を独立走査し、これら以外の数値 leaf と生 bool leaf は 0 件だった。これは今回の現行データと guard 反例を分ける確認であり、機密の完全な不存在証明ではない。

## 修正の適用境界

単純に key が `count` / `length` なら整数を許す分岐では不十分。上記 `{object:{length:123456}}` のように業務 schema field として同じ名称を持てるため、shape 文法上の位置を区別する必要がある。

- `object` 内の各 schema field 値は型タグまたは入れ子 shape のみに限定する。生の int/bool/float/null は不可。
- array の item shape に生 scalar を許さない。`str` / `int` 等の型タグは許す。
- 構造 wrapper の `length` と `[other-fields]` 等の構造 summary の `count` のみ、`type(value) is int` かつ非負を許す。
- `length` / `count` の正常 fixture を保持しつつ、raw amount/id と紛らわしい同名 schema field、bool counter を reject する回帰を追加する。

これは offline の小さい検査修正で実施できる。追加 API read・credential・runtime install は不要。

## 文脈の2仮説と解決

仮説 A: fixture は毎回別の private scalar scan と手動 review を通すため、公開 test は補助 guard にすぎない。

仮説 B: 公開 test を、将来担当者が匿名化 gate として直接使用する。

どちらでも構造位置に限定した整数検査は有益で、現在の正しい fixture を壊さず低コストで追加できる。従って BALTHASAR の修正要求を優先する。ユーザーの個人意図へ追加質問する必要はない。

## ◎ 評価

◎ BALTHASAR は「現行の漏洩」と「guard の見逃し」を分離し、70 tests pass を匿名化全域の成功へ膨らませず、実際の test method で反例を示した。この証拠により、追加 live call をせず継続運用の不足を修正できる。

◎ 初回の page detail / step status / filename collision / nested MCP / receipt の修正確認は今回の P2 で否定されない。今回の追加は fixture gate の範囲に限定する。

次工程: R1 を修正した別 pinned snapshot を独立再レビューし、正常構造値の保持と生数値拒否の両方を確認する。今回 report はその最終承認を先取りしない。
