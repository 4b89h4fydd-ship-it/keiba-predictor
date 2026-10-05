# ARVEXQ audits

このフォルダは、現行運用に関係する監査・障害記録だけを上位に置き、古い事前監査は `archive/` に分離します。

## Current

- `BUG_REPORT_2026-10-04.md` — 2026-10-04 時点の取得・同期・Cloudflare関連の障害整理。修正済み項目と未解決項目の確認用。

## Archive

- `archive/AUDIT_BOOT_SYNC_FIX.txt` — v324移行時のboot/sync修正の事前監査。
- `archive/AUDIT_V324.txt` — v324 core-data guard導入時の事前監査。

## 運用ルール

- 新しい障害調査は日付入りMarkdownで追加する。
- 解決済みで現行運用に不要になった監査は `archive/` に移す。
- Actionsの巨大ログや生成JSONはここへコミットせず、必要な場合だけ短期Artifactに保存する。
