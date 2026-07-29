# Node To Django Gap Report

## Migrated

- Auth register/login/me plus compatible `token` response.
- Business create/me/update.
- Competitor CRUD.
- Competitor post listing and mock generation.
- Trend listing and mock analysis.
- Content idea listing/generate/save/delete.
- Strategy latest/generate.
- Business analysis latest/generate.
- Feedback creation.
- Ownership filtering and cross-user access denial.
- Existing mock AI behavior.
- MongoDB migration command with dry-run support.
- OpenAPI docs.

## API Differences

- Django also returns `refreshToken` for login/register.
- Django uses UUID primary keys internally and exposes `_id` for compatibility.
- Validation detail shape is DRF-native under `details`, while the outer `{ success, message }` contract is preserved.

## Known Limitations

- PostgreSQL migration and end-to-end browser verification could not be completed in this environment because Docker daemon is not running and no local PostgreSQL server is available.
- The legacy Node backend has not been archived because full PostgreSQL verification is still pending.

## Remaining Work

- Run `docker compose up -d postgres` or connect a real PostgreSQL database.
- Run Django migrate/tests against PostgreSQL.
- Start Django on `8000` and Next.js with `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- Perform final browser smoke test.
