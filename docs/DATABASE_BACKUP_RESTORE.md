# Database Backup And Restore

Date: 2026-10-13

Status: procedure documented; v1.0.0 release restore drill **PASS** on 2026-10-13.

Never commit database dumps or credentials.

## Scope

The active staging database is Neon PostgreSQL. Railway data is archive/recovery-only and not part of active staging.

Backups should include:

- application tables
- `django_migrations`
- users/businesses
- AI generation records
- drafts/content records
- reports
- notifications

## Logical Backup

Use PostgreSQL custom format:

```bash
pg_dump "$DATABASE_URL" \
  --format=custom \
  --no-owner \
  --file=/secure/off-repo/backups/ai-business-growth-staging-YYYYMMDD.dump
```

Recommended verification:

```bash
sha256sum /secure/off-repo/backups/ai-business-growth-staging-YYYYMMDD.dump
pg_restore --list /secure/off-repo/backups/ai-business-growth-staging-YYYYMMDD.dump > /secure/off-repo/backups/ai-business-growth-staging-YYYYMMDD.manifest
```

Do not print `DATABASE_URL`.

## Restore To A Safe Target

Never restore over active staging without an explicit rollback decision.

Use a temporary local or free PostgreSQL target:

```bash
createdb ai_business_growth_restore_check
pg_restore \
  --dbname=ai_business_growth_restore_check \
  --no-owner \
  --clean \
  --if-exists \
  /secure/off-repo/backups/ai-business-growth-staging-YYYYMMDD.dump
```

Then verify:

```bash
psql "$RESTORE_DATABASE_URL" -c "select count(*) from django_migrations;"
psql "$RESTORE_DATABASE_URL" -c "select count(*) from accounts_user;"
psql "$RESTORE_DATABASE_URL" -c "select count(*) from businesses_business;"
psql "$RESTORE_DATABASE_URL" -c "select count(*) from ai_aicontentgeneration;"
psql "$RESTORE_DATABASE_URL" -c "select count(*) from content_planner_contentdraft;"
psql "$RESTORE_DATABASE_URL" -c "select count(*) from reports_report;"
psql "$RESTORE_DATABASE_URL" -c "select count(*) from notifications_notification;"
```

Compare counts with the source database. Use aggregate counts only; do not export personal data into release notes.

## Current Test Status

On 2026-10-13:

- PostgreSQL client tooling: PostgreSQL 16.15 from the official `postgres:16` Docker image.
- Source database: active Neon staging PostgreSQL 16.
- Backup command: custom-format `pg_dump --format=custom --no-owner --no-acl`.
- Backup timestamp UTC: `20261013T095808Z`.
- Backup size: `412005` bytes.
- Backup SHA-256: `3aea2440eb360e396353666dd08322625ca7e8fd6e32284e88d5e5ded3d47565`.
- Restore target: temporary local PostgreSQL 16 container.
- Restore test: PASS.
- Temporary restore database: destroyed after verification.

Safe aggregate verification:

| Table/group | Source | Restored |
| --- | ---: | ---: |
| `django_migrations` | 56 | 56 |
| users | 45 | 45 |
| businesses | 36 | 36 |
| content ideas | 464 | 464 |
| AI generations | 21 | 21 |
| background jobs | 8 | 8 |
| drafts | 56 | 56 |
| reports | 8 | 8 |
| notifications | 8 | 8 |

Additional checks:

- Expected tables found: 9/9.
- Orphan drafts: 0.
- Orphan AI generations: 0.
- Orphan reports: 0.
- Orphan notifications: 0.

The dump file remains outside Git. Do not commit dumps, copied database contents, or connection strings.
