# MAGI MELCHIOR 修正後相互批判 — 追加privacy finding

- 対象: 固定commit `497bacc46b7ca412e9fc0959ff37462720e772d6`、`private/review-revision`。
- 参照: 独立修正後reviewを保存した後に `private/magi-balthasar-revision.md` を読んだ。
- 対象指摘: BALTHASAR R1/P2、anonymous fixture guardの生数値許容。
- 検証: 合成fixture、一時directory、実testmethodのROOT mockのみ。ネットワーク/credential/実サービス/コード編集は0。

## 判定: changes_requested

BALTHASAR R1に同意。数値/booleanを型タグとして匿名化せずそのままschema fieldへ置いたfixtureが、実際のanonymous shape testを通過する。MELCHIORの先の修正後独立reportは`approved`だったが、この追加の再現可能なP2を踏まえ、R1修正と最終固定snapshotの再reviewまで承認を保留する。先のreportは履歴として書き換えない。

## 独立再現

`tests/test_catalog_snapshot.py`をimportして、`test_fixtures_are_only_anonymous_shape_not_response_values`そのものを呼んだ。各一時rootの`tests/fixtures/synthetic-shape.json`へ次のenvelopeを置き、`module.ROOT`だけをmockした。

```python
{
    'origin': 'observed_types_only',
    'case': 'synthetic',
    'tool': 'payment_product_detail_get',
    'shape': shape,
}
```

| shape | 実testの結果 | 期待 |
|---|---|---|
| `{'object':{'amount':123456,'id':9281}}` | accepted | raw業務値なので拒否 |
| `{'object':{'amount':True}}` | accepted | rawbooleanなので拒否 |
| `{'array':[9281],'length':1}` | accepted | raw配列要素なので拒否 |
| `{'object':{'length':9281}}` | accepted | object内の業務fieldなので拒否 |
| `{'object':{'data':{'array':['str'],'length':3}}}` | accepted | 正当なarray shapeの構造lengthとして許容 |
| `{'object':{'[other-fields]':{'count':74,'types':['int','str']}}}` | accepted | 正当な匿名field集約の構造countとして許容 |

全て合成値。実際の現fixtureに生の金額・IDが含まれているという結果ではない。

## 原因・優先度の批判

場所: `tests/test_catalog_snapshot.py:83`–84。`assertIsInstance(value,int)`は位置を確認しないため、構造length/countと業務schema fieldの生値が等しくpassする。Pythonではboolもintのsubclassなので、Trueもpassすることを再確認した。

P2が妥当。現在の漏洩やサービスのmutationは確認されておらず、privacy gateの将来の回帰検出不足である。P0/P1へ格上げする根拠はない。一方、「実額・IDを公開fixtureへ保存しない」という本taskの契約が検査対象であり、このtestが次の更新担当者へ渡されるため、単に仮想的な追加warningとして扱わず修正すべき。

仮説A: 毎回private生成と別秘密scan/manual reviewがあるため、通常の生成経路ではraw数値が入らない。仮説B: 将来担当者がfixtureを編集してsuiteを匿名化gateとして使う。Aでも今のtest名・検査目的と通過可能な内容が一致せず、Bでは混入を見逃す。追加API readやユーザーの意図確認は不要で、offline検査の修正で両方を改善できる。

## 修正提案と受入条件

キー名が`length`/`count`なら数値を許可するだけでは不十分。`{'object':{'length':9281}}`を実testが通したため、許可対象は形の文法上の構造位置で判定する必要がある。

- shape nodeは型タグ、object field map、array item shape、匿名field summaryとして検証する。
- object内schema fieldの値は型タグまたはnested shapeのみ。raw int/float/bool/string valueは拒否する。数値/booleanの業務値は`'int'`/`'float'`/`'bool'`等の型タグへ変換されている必要がある。
- array nodeのlength、および`[other-fields]` summaryのcountだけで、`type(value) is int`かつ非負の構造数値を許可する。
- array内要素はshape nodeとして検証し、raw数値を拒否する。
- object内に`length`/`count`という業務fieldがある場合も構造数値とは扱わず、型タグが必要。
- 正規fixtureの構造数値は残す。deduplicateしたitem_shapesと元配列lengthは一致しないことがあり、単純なlength==shape件数照合を導入しない。

上表の拒否ケースと正常構造count/lengthのpassを実validatorに対して回帰し、既存70suiteと新テストを新固定snapshotで再実行すれば受入可能。

## ◎ 相互批判の価値

初回のdynamic key漏れを直した後に、生値の数値経路が別に残ることをBALTHASARが独立探索で示した。現fixture漏れとは区別しながら、将来の更新gateの契約を具体的な合成入力で検証した点が適切。MELCHIORも元のapproved判断を維持せず、再現できた追加findingへ更新する。

初回のP1/P2修正（nested MCP、backup detail/step状態、HTTP receipt、dynamic keys）は解消済みという先の判断を維持する。R1が今回追加の修正条件。実サービスの全schema/timezone/個別契約検証は引き続き未確認のまま。
