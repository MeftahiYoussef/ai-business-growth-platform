# AI Business Growth & Trend Intelligence Platform Backend

Node.js, Express, MongoDB, Mongoose, JWT, and mock AI services for the Next.js frontend.

## Setup

```bash
cd backend
npm install
cp .env.example .env
npm run dev
```

Set `MONGO_URI` and `JWT_SECRET` in `.env` before starting.

## Scripts

- `npm run dev` starts the API with `nodemon`
- `npm start` starts the API with Node

## Base URL

```text
http://localhost:5000/api
```

## Auth

Register:

```http
POST /api/auth/register
Content-Type: application/json

{
  "fullName": "Demo Owner",
  "email": "owner@example.com",
  "password": "Password123!"
}
```

Login:

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "owner@example.com",
  "password": "Password123!"
}
```

Use the returned token for protected routes:

```http
Authorization: Bearer <token>
```

## Pagination, Search, Sorting

Supported on competitors, competitor posts, trends, and content ideas:

```text
?page=1&limit=10&search=ai&sortBy=createdAt&sortOrder=desc
```

## Notes

- Authentication is real JWT authentication with bcrypt password hashing.
- AI and social-media data are mocked.
- TODO comments mark where real AI APIs and social media provider APIs should be connected later.
- Each protected controller scopes data to the authenticated user's own business records.
