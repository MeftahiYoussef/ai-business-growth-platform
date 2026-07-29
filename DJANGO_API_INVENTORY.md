# Django API Inventory

All application endpoints except register/login/refresh require `Authorization: Bearer <token>`.

| Endpoint | Method | Body/query | Response |
| --- | --- | --- | --- |
| `/health` | GET | none | `{ success, status }` |
| `/api/auth/register` | POST | `fullName`, `email`, `password`, optional `role` | `{ success, token, refreshToken, data: user }` |
| `/api/auth/login` | POST | `email`, `password` | `{ success, token, refreshToken, data: user }` |
| `/api/auth/me` | GET | none | `{ success, data: user }` |
| `/api/auth/refresh` | POST | `refresh` | `{ success, token }` |
| `/api/auth/logout` | POST | optional `refresh` | `{ success }` |
| `/api/business` | POST | business profile fields | `{ success, data: business }` |
| `/api/business/me` | GET | none | `{ success, data: business|null }` |
| `/api/business/:id` | PUT | partial business fields | `{ success, data: business }` |
| `/api/competitors` | GET | `page`, `limit`, `search`, `sortBy`, `sortOrder` | `{ success, items, pagination }` |
| `/api/competitors` | POST | `businessId`, `name`, `platform`, optional metrics | `{ success, data: competitor }` |
| `/api/competitors/:id` | GET/PUT/DELETE | id in path | resource envelope |
| `/api/competitors/:id/posts` | GET | pagination/search/sort query | `{ success, items, pagination }` |
| `/api/competitors/:id/posts/mock-generate` | POST | optional `count` | `{ success, data: posts[] }` |
| `/api/trends` | GET | pagination/search/sort query | `{ success, items, pagination }` |
| `/api/trends/analyze` | POST | `businessId` | `{ success, data: trends[] }` |
| `/api/content-ideas` | GET | pagination/search/sort query | `{ success, items, pagination }` |
| `/api/content-ideas/generate` | POST | `businessId`, optional `count` | `{ success, data: ideas[] }` |
| `/api/content-ideas/:id/save` | PUT | id in path | `{ success, data: idea }` |
| `/api/content-ideas/:id` | DELETE | id in path | `{ success, data: { id } }` |
| `/api/strategy` | GET | none | `{ success, data: strategy|null }` |
| `/api/strategy/generate` | POST | `businessId` | `{ success, data: strategy }` |
| `/api/analysis` | GET | none | `{ success, data: analysis|null }` |
| `/api/analysis/generate` | POST | `businessId` | `{ success, data: analysis }` |
| `/api/feedback` | POST | `businessId`, `contentIdeaId`, `liked`, optional `comment` | `{ success, data: feedback }` |

Errors use:

```json
{ "success": false, "message": "Validation failed", "details": {} }
```
