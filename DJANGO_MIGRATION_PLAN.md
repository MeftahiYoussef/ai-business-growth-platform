# Django Migration Plan

## Existing Node Architecture

- Express app in `backend/src/app.js`
- JWT auth middleware checks `Authorization: Bearer <token>`
- MongoDB/Mongoose models for users, businesses, competitors, posts, trends, ideas, strategies, analyses, and feedback
- Mock AI service generates deterministic sample posts, trends, ideas, strategies, and SWOT analyses
- Responses use `{ success, data }` or `{ success, items, pagination }`

## New Django Architecture

- Django project: `django-backend/config`
- Apps: `accounts`, `businesses`, `competitors`, `competitor_posts`, `trends`, `content_ideas`, `strategies`, `analyses`, `feedback`, `ai`
- PostgreSQL through Django ORM
- Django REST Framework with Simple JWT
- Compatibility serializers expose `_id`, camelCase fields, and existing pagination structure

## Endpoint Mapping

| Existing endpoint | Method | Django implementation |
| --- | --- | --- |
| `/api/auth/register` | POST | `apps.accounts.views.RegisterView` |
| `/api/auth/login` | POST | `apps.accounts.views.LoginView` |
| `/api/auth/me` | GET | `apps.accounts.views.MeView` |
| `/api/business` | POST | `apps.businesses.views.BusinessCollectionView` |
| `/api/business/me` | GET | `apps.businesses.views.MyBusinessView` |
| `/api/business/:id` | PUT | `apps.businesses.views.BusinessDetailView` |
| `/api/competitors` | GET/POST | `apps.competitors.views.CompetitorListCreateView` |
| `/api/competitors/:id` | GET/PUT/DELETE | `apps.competitors.views.CompetitorDetailView` |
| `/api/competitors/:id/posts` | GET | `apps.competitors.views.CompetitorPostsView` |
| `/api/competitors/:id/posts/mock-generate` | POST | `apps.competitors.views.CompetitorPostsGenerateView` |
| `/api/trends` | GET | `apps.trends.views.TrendsView` |
| `/api/trends/analyze` | POST | `apps.trends.views.AnalyzeTrendsView` |
| `/api/content-ideas` | GET | `apps.content_ideas.views.ContentIdeasView` |
| `/api/content-ideas/generate` | POST | `apps.content_ideas.views.GenerateContentIdeasView` |
| `/api/content-ideas/:id/save` | PUT | `apps.content_ideas.views.SaveContentIdeaView` |
| `/api/content-ideas/:id` | DELETE | `apps.content_ideas.views.DeleteContentIdeaView` |
| `/api/strategy` | GET | `apps.strategies.views.StrategyView` |
| `/api/strategy/generate` | POST | `apps.strategies.views.GenerateStrategyView` |
| `/api/analysis` | GET | `apps.analyses.views.AnalysisView` |
| `/api/analysis/generate` | POST | `apps.analyses.views.GenerateAnalysisView` |
| `/api/feedback` | POST | `apps.feedback.views.FeedbackView` |

## Compatibility Issues

- Django uses UUID primary keys; original MongoDB IDs are preserved in `legacy_mongo_id`.
- API responses include `_id` for existing frontend compatibility.
- Django auth returns `token` like Express and also returns `refreshToken`.
- No permanent frontend route redesign was required.
