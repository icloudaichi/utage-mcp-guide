# MAGI MELCHIOR 相互批判

- 対象は初回固定commit `5a65fe111afb187e28459ec78931d9a9605c5098` / `private/review-initial` のみ。修正中workingtreeは見ていない。
- 参照: `private/magi-caspar-initial.md`、`private/magi-balthasar-initial.md`。独立初回reportを確定・保存後に参照した。
- 確認はoffline合成応答・mockのみ。ネットワーク/credential/実サービス/コード編集なし。

## CASPAR指摘への批判

### 空ページ詳細をcompleteとするP1 — 同意、3者独立再現で統合

MELCHIOR M2 / BALTHASAR B1と同一問題。`data={}`だけでなくwrong ID、content_type別のbody欠落も同じ検査不足として扱うべき。各再現はscopeを増やす別findingではなく、必要な回帰の境界ケースになる。

CASPARはmainのexit0/completeまで再現しており、MELCHIORのbackup_funnel errors0からmainへ伝播する分析を補強した。P1妥当。公式page schemaをこのレビューで取得していない点は別記し、mock成功を仕様適合の根拠にしない。

### step completeとdetail failureの矛盾P2 — 同意、独立再現

`api_get`へsteps/page list成功→page detail `None`の3応答をmockして`backup_funnel`を実行。結果は `{'steps':1,'pages':1,'errors':1}`、step `_meta.md`に`status: complete`が残ることを再確認した。

仮説A「一覧取得のstatus」の解釈も可能だが、field名は単に`status`であり、summary/manifestと同じcomplete/incomplete語彙を使用する。下位directoryだけを再利用する読者に誤認を与えるため、全体失敗が正しくてもP2は成立する。detail終了後にstep statusを更新する修正が最小で、複数status体系を作る必要はない。

### filename collision — 既存制約としての扱いに同意

IDを含まない同名パスはbaselineにもあるため、今回の新たなfilename defectとはしない判断は適切。ただし新manifestの`complete`を「全resourceが独立ファイルとして保存された」と読む運用では不正確になる。修正対象へ拡大するならIDによる一意なパス、拡大しないなら保存範囲の限界を明記する。単に新bugとしてP1へ格上げしない。

## BALTHASAR指摘への批判

### backup空detail P1 — CASPAR/MELCHIORと統合

重複findingを3件とは数えず、独立裏付け3本として集約する。

### success型とHTTP receipt P2 — 同意、適用境界を分ける

追加offline実行で、`unwrap_result({'success':value,'data':[]},...)`がvalue=`'false'`、`0`、`None`、`[]`、`{}`の全てに対して`success=True`を返すことを再現。型不正をFalseと推定するのではなく、`success`がenvelopeに存在するならbool以外をinvalid_resultへ落とすべき。

一方で一般の業務record配下の`success` fieldまで一律にenvelopeの意味へ解釈するのはschema未確認のため注意が必要。既存`_error_marker`は再帰的なので、最小修正では対応位置の厳格化を回帰テストで示し、将来はenvelope正規化とbusiness data検査を分けることを勧める。

HTTP非2xxのsuccess receiptはMELCHIOR M3と同一で、正常なunwrap経路が401を拒否することからP2妥当。`CheckedResult`の手動構築を外部観測で許すAPIである以上、make_receiptの成功不変条件も明示して補強する。HTTP値Noneは未保存として許容し、仮の200を作らない。

親の速報ではsuccess型findingがP1と要約されていたが、BALTHASAR確定reportはB2=P2。MELCHIORとしては通常経路の非2xx拒否が成立し、現在のlive応答が型不正だった証拠がないため、B2をP2として統合することに同意する。これとは別に標準JSON-RPC→MCP envelopeを取りこぼすM1はP1を維持する。

### privacy fixture dynamic key P2 — 同意、現fixture漏えいとは区別

既存walk判定を合成shape `{'synthetic-Bearer-token-value':'string'}`へ適用するとpassすることを再現。`@`の禁止だけではtoken/契約ID/電話番号/氏名のキーを拒否できない。公開投影関数が固定schema name allowlistを持つので、fixtureテストにもそのルールを共有して更新時のprivacy回帰を防ぐのが合理的。

ただしこの指摘はfuture regressionの弱さであり、現在公開fixtureに実secretがあるという根拠ではない。またfixtureは公開投影helperと異なる形式であるため、既存構造keyを誤って禁止しないよう、構造keyと公開schema keyのallowlistを分ける必要がある。

## 相互批判で追加する観点

MELCHIOR M1のnested content問題は、BALTHASARのsuccess型問題と「未検証成功の保存」という影響が共通だが根本原因は異なる。単なるsuccess bool checkではnested profile/http status/nonJSONを止められない。全wrapper depthのMCP content正規化と、signal型検査の両方を実装・回帰する必要がある。

## 統合提案

| 優先度 | 統合アクション | 出典 |
|---|---|---|
| P1 | 全depthのMCP content/structuredContentを展開しidentity/status/errorを検査、未知本文をfail closed | MELCHIOR M1 |
| P1 | page detail ID/content_type/bodyの検査、欠落をbackup incompleteへ伝播 | 3者共通 |
| P2 | step statusをdetail結果へ連動 | CASPAR |
| P2 | success型とreceipt非2xx成功矛盾の拒否 | BALTHASAR B2 / MELCHIOR M3 |
| P2 | fixture動的keyを固定allowlistで拒否する回帰 | BALTHASAR B3 |

filename collisionは既存制約として記録し、新manifest completeの保証範囲を明示するか一意パスへ改善する。修正が行われた場合は再reviewで確認する。

最終承認は修正後固定commitの再reviewまで保留。追加live呼出しを要求するfindingはなく、全て標準Pythonとmockで検証可能。
