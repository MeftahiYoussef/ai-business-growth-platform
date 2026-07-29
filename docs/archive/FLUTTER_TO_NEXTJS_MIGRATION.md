# Flutter To Next.js Migration Report

## Migration Inventory

| Flutter screen | Flutter route | Next.js route | Main components | API endpoints | Auth | Data source in Flutter | Browser differences |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Splash | `/splash` | middleware + redirects | middleware, dashboard layout | `GET /api/auth/me`, `GET /api/business/me` | Public bootstrap | real auth call | No dedicated splash page; middleware/server guard handles restoration |
| Login | `/login` | `/login` | `AuthCard`, `LoginForm`, `TextField` | `POST /api/auth/login`, `GET /api/auth/me` | Public | real backend | JWT stored in httpOnly cookie rather than browser storage |
| Register | `/register` | `/register` | `AuthCard`, `RegisterForm` | `POST /api/auth/register` | Public | real backend | Same labels and validation, password visibility added |
| Forgot password | `/forgot-password` | `/forgot-password` | `AuthCard` | none | Public | placeholder | Same unimplemented behavior |
| Business Onboarding | `/onboarding` | `/onboarding` | `OnboardingForm`, `AppCard` | `POST /api/business`, `GET /api/business/me` | Protected | real backend | CSS step form instead of Flutter PageView |
| Dashboard | `/dashboard` | `/dashboard` | `Shell`, `MetricCard`, `AppCard` | business, competitors, trends, content ideas | Protected | mixed real/mock fallback | Backend data replaces counters where endpoints exist |
| Competitors | `/competitors` | `/competitors` | responsive table/cards, add dialog | competitor CRUD, search/sort/pagination | Protected | real + fallback in Flutter | Uses responsive HTML table/card layout |
| Competitor detail | `/competitors/:id` | `/competitors/[id]` | detail cards, post list | get competitor, posts, mock-generate posts | Protected | real posts where generated | Hooks/hashtags derived from backend posts |
| Trends | `/trends` | `/trends` | trend cards | `GET /api/trends`, `POST /api/trends/analyze` | Protected | real + fallback in Flutter | Empty state instead of mock data when no backend records |
| Content Generator | `/generate` | `/generate` | idea cards | content list/generate/save/delete | Protected | real + fallback in Flutter | Clipboard uses browser API |
| Strategy | `/strategy` | `/strategy` | calendar, info cards, ranked actions | strategy get/generate | Protected | real + fallback in Flutter | Backend strategy rendered when present |
| Business Analysis | `/analysis` | `/analysis` | SWOT cards, recommendation rows | analysis get/generate | Protected | real + fallback in Flutter | Backend analysis rendered when present |
| Profile / Settings | `/profile`, `/settings` | `/profile` | profile cards, theme toggle, logout | business me, logout | Protected | real business + placeholders | Theme toggle is DOM CSS-variable based |

## Components Created

- `Shell`, desktop sidebar, top header, mobile bottom navigation
- `AuthCard`, `LoginForm`, `RegisterForm`, `OnboardingForm`
- `AppCard`, `Button`, `SectionTitle`, `MetricCard`, `EmptyState`
- Responsive competitors table and mobile cards
- Toast provider for mutation feedback

## API Endpoints Connected

- Auth: register, login, me, logout proxy
- Business: create, me, update module
- Competitors: list, create, get, delete, posts, mock-generate
- Trends: list, analyze
- Content Ideas: list, generate, save, delete
- Strategy: get, generate
- Analysis: get, generate
- Feedback: API module created for `POST /api/feedback`

## Mock Data Removed

Backend calls now drive business, competitor, competitor post, trend, content idea, strategy, and analysis views. Static text remains only for Flutter placeholder UI areas such as subscription, usage, and default empty recommendation copy.

## Verified Features

- Type-safe API modules
- Server-side protected layout
- Middleware route protection
- Cookie-based auth proxy
- Responsive desktop sidebar and mobile bottom navigation
- Form validation for auth and onboarding

## Platform-Specific Differences

- Next.js uses route middleware and server layout checks instead of Flutter splash-driven navigation.
- JWT is stored in an httpOnly cookie for better web security.
- Flutter Material icons are represented with `lucide-react` equivalents.
- Flutter DataTable becomes an accessible HTML table with mobile card fallback.

## Remaining Work

- Add deeper end-to-end browser automation for every route after dependency installation and backend startup.
- Deploy with HTTPS so cookies can be marked `Secure`.
