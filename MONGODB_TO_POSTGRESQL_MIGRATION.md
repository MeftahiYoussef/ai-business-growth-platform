# MongoDB To PostgreSQL Migration

## Prerequisites

- Django migrations applied to PostgreSQL.
- `MONGODB_URI` points to the existing MongoDB database.
- `DATABASE_*` variables point to the PostgreSQL target.

## Commands

Dry run:

```bash
cd django-backend
.venv/bin/python manage.py migrate_from_mongodb --dry-run
```

Apply:

```bash
.venv/bin/python manage.py migrate_from_mongodb
```

## ID Mapping

Every migrated model stores the original MongoDB ObjectId in `legacy_mongo_id`. Relationships are resolved by looking up related records through that field, then writing proper PostgreSQL foreign keys or many-to-many rows.

## Password Strategy

Node bcrypt hashes are stored as `bcrypt$<original_hash>`. `NodeBcryptPasswordHasher` verifies these hashes during login. New password writes use Django PBKDF2.

## Rollback

The legacy Express backend remains in `backend/`. Do not delete it until:

- Django is verified against PostgreSQL.
- The frontend has passed smoke tests against Django.
- Migrated record counts have been reviewed.

## Verification

Compare counts for each MongoDB collection against PostgreSQL tables, then run an authenticated smoke flow through the frontend.
