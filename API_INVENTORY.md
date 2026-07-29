# API Inventory

All endpoints below require bearer authentication unless marked public.

| Endpoint | Method | Permission | Input | Output |
| --- | --- | --- | --- | --- |
| `/api/auth/register` | POST | Public | `fullName`, `email`, `password` | `{ success, token, refreshToken, data }` |
| `/api/auth/login` | POST | Public | `email`, `password` | `{ success, token, refreshToken, data }` |
| `/api/auth/me` | GET | Authenticated | none | `{ success, data }` |
| `/api/business` | POST | Authenticated | business profile | `{ success, data }` |
| `/api/business/me` | GET | Authenticated | none | `{ success, data|null }` |
| `/api/competitors` | GET/POST | Business access | pagination/body | paginated or envelope |
| `/api/competitors/compare` | GET | Business access | optional filters | `{ success, data[] }` |
| `/api/trends` | GET | Business access | pagination | paginated trends |
| `/api/content-ideas/generate` | POST | Business access | `businessId`, `count` | generated ideas |
| `/api/team` | GET | Business access | `businessId?` | members |
| `/api/team/invite` | POST | Owner/Admin | `businessId`, `email`, `role` | invitation |
| `/api/team/invitations/:token/respond` | POST | Invitee | `accept` | invitation |
| `/api/integrations/connections` | GET/POST | Business access | `businessId`, `provider` | connections |
| `/api/integrations/connections/:id/sync` | POST | Business access | none | sync job |
| `/api/integrations/accounts` | GET | Business access | `businessId?` | accounts |
| `/api/integrations/posts` | GET | Business access | `businessId?` | posts |
| `/api/analytics/summary` | GET | Business access | filters | metrics summary |
| `/api/analytics/goals` | GET/POST | Business access | goal fields | goals |
| `/api/ai/studio/generate` | POST | Business access | generation prompt | generation |
| `/api/ai/studio/history` | GET | Business access | `businessId?` | generations |
| `/api/ai/content-plans/generate/` | POST | Business content-write role | `business_id`, `platforms`, `start_date`, optional `goal`, `additional_instructions` | seven-day plan, provider metadata, token usage |
| `/api/ai/content-plans/:id/create-drafts/` | POST | Business content-write role | `item_day_numbers`, optional `edited_items` | created content drafts |
| `/api/planner/drafts` | GET/POST | Business write | draft fields | drafts |
| `/api/planner/drafts/:id/request-review` | POST | Business write | none | draft |
| `/api/planner/drafts/:id/approve` | POST | Approver role | none | draft |
| `/api/planner/drafts/:id/schedule` | POST | Business write | `scheduledAt` | draft |
| `/api/reports` | GET/POST | Business access | report config | reports |
| `/api/notifications` | GET | Business access | none | notifications |
| `/api/notifications/:id/read` | POST | Owner notification | none | notification |

## AI Content Plan Response

Successful generation returns:

```json
{
  "success": true,
  "id": "generation-id",
  "status": "completed",
  "provider": "groq",
  "model": "configured model",
  "prompt_version": "content-plan-v1",
  "plan": {
    "summary": "...",
    "primary_goal": "engagement",
    "target_audience": "...",
    "items": []
  },
  "usage": {
    "input_tokens": 0,
    "output_tokens": 0
  }
}
```

Errors follow the standard `{ success: false, message, details? }` format. Application quotas return `429`; provider failures return `502`; provider timeouts return `504`.
