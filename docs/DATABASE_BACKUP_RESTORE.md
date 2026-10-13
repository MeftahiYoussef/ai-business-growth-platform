# Database Backup And Restore

Date: 2026-10-13

Status: procedure documented; restore test is **NOT_FULLY_TESTED** in this workspace because no local Neon connection string or PostgreSQL client tools were available.

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

- Local Neon connection file: absent.
- `pg_dump`: unavailable in the execution environment.
- `pg_restore`: unavailable in the execution environment.
- Restore test: NOT_FULLY_TESTED.

Required before v1.0.0 tag:

- install/use PostgreSQL client tools in a secure environment
- run a staging logical dump
- validate manifest contains expected tables
- restore into a safe temporary database or inspect dump structure
- compare safe aggregate counts
