# Item 002 progress

- Item: 2, NAR馬場状態解析
- Current status: `分離済`; not production verified
- Main code fix merged by PR #336, main SHA `13a579b` (full: `13a579bfb21f60315205aee96cec8998b3fd013b`)
- CI: PR #336 checks `39116527870`, `39116527880`, `39116527921` succeeded
- Fix: official Banei `馬場：1.0` is preserved as `goingMoisture`; it is not inferred as 良/稍重/重/不良
- Production finding: `nar-2026-10-17-帯広ば-01` currently returns `condition=不明`, `goingMoisture=null`
- Official source read directly: `https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/RaceMarkTable?k_babaCode=03&k_raceDate=2026/10/17&k_raceNo=1` contains `馬場：1.0`
- API deploy attempts `39116660246`, `39117035988`, `39117507202`, `39117843198` stopped at the production source guard; no D1 write was performed
- Latest preflight: `39117680002`; production source drifted between preflight and deploy attempts
- Do not mark item 002 complete until the deployed API readback returns observed `goingMoisture` for all applicable Banei races
- Next command: run preflight, capture the latest `kraiz-api` `sourceSha256`, then immediately dispatch `ARVEXQ API Private Storage Audit Deploy` with `-f expected_source_sha256=<captured SHA> -f verify_only=false`; inspect `https://kraiz-api.4b89h4fydd.workers.dev/api/race/nar-2026-10-17-%E5%B8%AF%E5%BA%83%E3%81%B0-01`
