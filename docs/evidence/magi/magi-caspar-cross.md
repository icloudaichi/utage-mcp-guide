# MAGI 相互批判 — CASPAR

- 対象 pinned initial: `5a65fe111afb187e28459ec78931d9a9605c5098`
- 固定 snapshot: `private/review-initial`
- 確認時刻: 2026-10-03 07:20 UTC
- 入力: 親から共有された MELCHIOR / BALTHASAR の初回独立 findings。修正版 workingtree は読んでいない。
- 手段: Python 標準ライブラリによる synthetic mock / 純関数呼出し。ネットワーク・実サービス・credential なし、コード編集なし。

## 他者指摘の再現と優先度

### MELCHIOR: nested JSON-RPC `result.content` の検査漏れ — P1 を支持

位置: `scripts/contract_checks.py:246-261,300-306,321-339`。

root の `content` は decode するが、JSON-RPC の `result` 以下の CallToolResult の `content` は envelope traversal に含まれない。最終 payload が `{content:[...]}` という mapping のままなので、有効な business payload と誤認する。JSON-RPC→MCP CallToolResult は対象関数が掲げる通常の wrapper 形であり、特殊な攻撃ケースだけではない。

共通入力 outer: `{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":TEXT}]}}`。期待 tool=`find_tools` / profile=`lbs`。

| TEXT（合成） | 初回 snapshot の結果 | 本来の判定 |
|---|---|---|
| `not json` | success True / marker null / HTTP null | invalid_result |
| JSON `profile=wasamagazine,data=[]` | success True / marker null / HTTP null | profile_mismatch |
| JSON `http_status=500,data=[]` | success True / marker null / HTTP null | http_error |
| JSON `success=true` のみ | success True / marker null / HTTP null | invalid_result |

4 ケースすべて payload keys は `["content"]`。外側が成功なら失敗を覆い隠せるため P1。metadata と実 read の証拠を区別する今回の PR の土台に直接影響する。

CASPAR 補足: wrapper を一段ずつ同じ規則で decode し、すべての identity / HTTP / error を検査する共通化が適切。単に各例へ個別分岐を足すと wrapper の組合せで再び漏れる。mock で depth・複数 content・structuredContent 併記・result/body/content の混在を再確認できるため live call の追加は不要。

### BALTHASAR: `success='false'` の型違い — 指摘を支持、P2

位置: `scripts/contract_checks.py:179-180`。

`{"success":"false","data":[]}` は `is False` に一致せず、success True / marker null になる。`isError` にある boolean 型検査と一貫していない。明示された成功・失敗 flag が不正な型なら unverified/invalid_result とする regression が必要。

適用境界: wrapper の `success` flag に対する型検査。resource の独自 field に同名キーがあるかは全 output schema 未取得のため判断できない。JSON validity が success を証明しないというドキュメント上の方針に沿って reject するのが適切。

### BALTHASAR / MELCHIOR: success receipt と HTTP 401 の矛盾 — 指摘を支持、P2

位置: `scripts/contract_checks.py:363-369`。

`make_receipt(build_read_plan('find_tools','lbs'), CheckedResult(True,None,401), verification_kind='live_read')` は `status: success,http_status:401` を返す。401 の範囲・型は有効なので、success と HTTP の意味的不整合を見落とす。

重要な適用境界: 通常の `execute_read_plan`→`unwrap_result` 経路では 401/403 を先に blocked_auth とするため、この receipt 偽成功には手生成／他経路の CheckedResult が必要。現在の live receipt がこの helper から生成されたと断定しない。P1 nested wrapper defect と同じ緊急度の実観測障害と混同せず、公開 factory の invariant を強める P2 とする。

修正案: success と non-2xx HTTP の組合せを reject、boolean success / marker consistency / fixed marker 範囲と合わせて検査。パブリック receipt に inconsistent success を出さない mock を追加する。

## CASPAR 初回 findings と比較

- 全 3 者が独立に空 page detail の誤 complete を再現した。P1 を維持する。詳細型を確認せず default 値で埋めた結果を完了扱いすることが問題である。
- CASPAR の step metadata complete の問題は全体 manifest が正しく失敗しても残る。page-list-only status か全 step の status かをコードで明示できるため、ユーザーへの追加質問は不要。
- filename collision は baseline 由来。今回の新しい complete の保証範囲と関係するが、新規バグとして他者の P1 より優先しない。記録するか検知する方法が適切。

## 修正時の適用境界に関する未確定事項

同じ initial helper に synthetic `data:[{id:'sample',status:'failed'}]` と `data:[{id:'sample',success:false}]` を入力すると、ともに tool_error になる。これは追加の live endpoint の不具合を観測した証拠ではない。

仮説 A: `status` / `success` は business record の独立した属性で、リスト取得自体は成功し得る。現在の全 resource 再帰判定は false negative と不要な再取得を生む。

仮説 B: その schema では status / success は provider error envelope の信号であり、現在の reject が正しい。

全 output schema 未捕獲のため、どちらかへ断定しない。修正を wrapper 検査へ集中し、business records を wrapper と扱わない境界を説明する必要がある。完全 schema 取得がこの PR の追加必須条件とはしない。

## ◎ 評価と優先アクション

◎ 3 者の独立再現が一致した空 detail 問題を先に直し、追加 live call を増やさず wrapper の mock を増やす方向は適切。変更系 133 件を mock で拒否する基盤を維持でき、検証コストと誤 success のリスクを同時に下げられる。

| 優先度 | アクション | 期限 | 根拠 |
|---|---|---|---|
| P1 | ページ detail の identity・content schema を検査し欠落を incomplete にする | 修正後再レビュー前 | 全 3 者が空 detail の exit 0 を独立再現 |
| P1 | nested JSON-RPC/MCP wrapper を共通の判定へ通す | 修正後再レビュー前 | nonJSON/profile mismatch/HTTP500/success-only が success |
| P2 | wrapper flag の boolean 型と receipt の success/HTTP 整合を検査する | 修正後再レビュー前 | string false と synthetic HTTP401 receipt の再現 |
| P2 | step 完了状態を detail 結果へ連動させるか一覧状態として明示する | 修正後再レビュー前 | global incomplete / step complete の独立再現 |

相互批判としての結論: 他者の事実指摘を支持する。優先度は通常経路の nested 検査漏れを P1、手生成 CheckedResult の receipt invariant を P2 と分ける。個人目標の問いかけは不要。実 schema と実 backup は引き続き未検証であり、修正版 pinned commit の再レビューを待つ。
