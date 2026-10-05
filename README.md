# ARVEXQ Cloudflare API

This branch contains the Cloudflare Worker + D1 serving layer for ARVEXQ.

## Production resources

- Worker resource: `kraiz-api` (legacy infrastructure name; intentionally retained)
- D1 database: `kraiz-prod` (legacy infrastructure name; intentionally retained)
- Worker source: `worker.js`
- Wrangler config: `wrangler.jsonc`
- D1 binding: `DB`

Do not rename the Worker or D1 resource only for branding. The existing names are part of the deployed endpoint/data wiring and should be changed only as a planned migration.

## Commands

```bash
npm install
npm run check
npm run dev
npm run deploy
```

`npm run check` performs a JavaScript syntax check without touching Cloudflare.

## API role

The Worker is the durable API/D1 layer used by ARVEXQ sync jobs and the PWA. Current routes include health, day/race reads, odds reads, and authenticated sync writes.

## Branch separation

- `main`: Python collection/prediction/static PWA and GitHub Actions
- `cloudflare`: Worker/D1 API only

Do not merge `main` wholesale into `cloudflare` or vice versa.
