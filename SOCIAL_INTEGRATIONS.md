# Social Integrations

## Supported Providers

- Sandbox: implemented for development.
- Instagram Business/Creator: provider slot prepared, real OAuth deferred.
- Facebook Pages: provider slot prepared, real OAuth deferred.
- LinkedIn company pages: provider slot prepared, real OAuth deferred.

## Credentials

Do not commit credentials. Future real providers should use environment variables such as:

- `INSTAGRAM_CLIENT_ID`
- `INSTAGRAM_CLIENT_SECRET`
- `FACEBOOK_CLIENT_ID`
- `FACEBOOK_CLIENT_SECRET`
- `LINKEDIN_CLIENT_ID`
- `LINKEDIN_CLIENT_SECRET`

## OAuth Flow

The model supports account selection, encrypted token storage fields, expiration tracking, refresh token storage, revocation status, required permission display, and health status.

## Sandbox Behavior

Connecting `sandbox` creates a development account, posts, account snapshots, and post snapshots. This data is explicitly fake and should not be shown as real provider data.

## Synchronization

The current sync endpoint completes synchronously and updates `lastSuccessfulSyncAt`. Celery/Redis scheduled sync is in the Phase 2 backlog.
