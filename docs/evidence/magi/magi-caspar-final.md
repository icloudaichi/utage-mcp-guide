# MAGI 最終固定版レビュー — CASPAR

## 判定

**approved** — 対象 commit `25aaf49eaf83fb8f9e2cf2c063a9a21e0a5027e1`。

BALTHASAR R1 / CASPAR 相互批判 P2 の fixture guard 不足は修正された。9 件の不正 synthetic shape を実際の fixture test で拒否し、3 件の正常匿名構造を受理することを独立再現した。今回の検査で新しい対応必須 P0/P1/P2 を確認していない。

## 固定性・独立性

- 対象 snapshot: `workspace/private/review-final` のみ。
- レビュー証拠確認時刻: 2026-10-03 07:39 UTC。
- 他者の final report と workingtree は未参照。
- 既読の実 magi_reviewer prompt / SKILL を継続適用し、検証効率・完了判定を担当。
- ネットワーク・実サービス・credential・依存取得 0。コード編集 0。

## R1 の修正と独立再現

位置: `tests/test_catalog_snapshot.py:74-116`。

再帰 shape 文法を用い、schema field にある raw leaf と構造 wrapper の整数を区別する。`array.length` と `object.[other-fields].count` の値だけ、exact int かつ非負を受理する。Python bool は int の subclass でも受理しない。型タグは固定集合と照合し、未知の container/summary key は拒否する。

前回と同じ再現方法を使用した。final snapshot の実際の test module を import し、temporary directory に synthetic fixture を作成、module の `ROOT` のみ mock し、`test_fixtures_are_only_anonymous_shape_not_response_values` をそのまま呼んだ。validator のコピーや改変は行っていない。

| 合成ケース | 最終版の実結果 |
|---|---|
| raw amount 123456 / id 9281 | reject |
| schema field の raw bool | reject |
| array の raw numeric value | reject |
| object field length の raw integer | reject |
| object field count の raw integer | reject |
| structural length=true | reject |
| structural length=-1 | reject |
| 入れ子の array numeric ID | reject |
| structural count=1.0 | reject |
| 型タグ object + array length 1 + unknown-field summary count 2 | accept |
| empty array length 0 + summary count 0/types empty | accept |
| array_item_shapes 内の正常 object 型タグ | accept |

12 synthetic cases はすべて期待した結果だった。BALTHASAR の元反例、CASPAR が追加した bool/array/同名 field/不正構造整数の反例を止め、正しい fixture 構造を維持できている。

## テストと性能

final snapshot で実行:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
Ran 73 tests in 0.079s
OK
```

◎ R1 対応は guard の文法と 3 件の回帰 test に限定され、fixture の再取得や API 呼出しを増やしていない。構造用 count/length を全面禁止せず、必要な情報を保持したまま numeric leak の見逃しを防げる。

◎ 73 tests には初回の page detail / step status / ID hash collision / nested MCP / receipt invariant の回帰も含まれ、すべて再度 pass した。追加 guard のために既存の修正が退行した証拠はない。全 suite は 1 秒未満で維持され、将来の文書更新時にも実行しやすい。

◎ malformed container/summary の exact key 検査も加わったため、raw 値を別の辞書に包んで整数条件だけを通す余地を抑えている。新しい schema field を必要とする場合は allowlist と匿名化 grammar を明示的に更新する契約になる。

## 未検証範囲とブロッカー

承認はこの固定 commit の文書・offline 契約・コードに対する判断。全 endpoint の live 成功や完全な機密不存在を証明するものではない。

- inputSchema/outputSchema/annotations 全体は未捕獲。
- timezone 保証と submitted_at の公開保証は未確認。created_at と submitted_at を同一視しない。
- 購入者ごとの個別 subscription status / 次回課金 / 決済代行 subscription ID は未取得。商品 plan 設定から算出・代用しない。
- auth blocked は解消確認していない。非JSON診断 receipt は unverified のまま。成功へ書き換えていない。
- 実 backup、実 write、完全 API schema 適合は未検証。73 tests は offline の成功。
- private credential literal scan を reviewer として再実行していない。今回アクセスした fixture は public 匿名型構造と synthetic 値のみ。

この pinned commit に対する対応必須 review findings は 0 件。CASPAR の最終レビュー上のブロッカーはない。
