# Architecture

## Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend + API | Next.js 16 (App Router) | Full-stack SSR, Vercel-native, API routes co-located |
| Database | Neon PostgreSQL + Prisma ORM | Serverless-compatible, parameterized queries prevent SQLi |
| Authentication | Clerk | MFA, social login, session management out-of-box |
| Deployment | Vercel | Preview deploys per PR, zero-config Next.js |
| ML Pipeline | Python (FastAPI + scikit-learn) | Offline; seeds predictions into PostgreSQL |

## Data Flow

```
Browser (React SPA)
  └─ HTTP ──► Next.js App Router (Vercel)
                  ├─ app/page.tsx          (public: match calendar)
                  ├─ app/(auth)/stats/     (Clerk-protected)
                  ├─ app/(auth)/settings/  (Clerk-protected)
                  └─ app/api/*             (route handlers)
                       └─ Prisma Client ──► Neon PostgreSQL
                                               ├─ Match (predictions + probabilities)
                                               ├─ Player (composite scores)
                                               └─ PipelineMetrics (model accuracy)

Python ML Pipeline (local, offline)
  goals_app/ → scikit-learn models → predictions → scripts/seed_db.ts → PostgreSQL
```

## User Roles

| Role | Access | Auth |
|------|--------|------|
| Guest | Match calendar, W/D/L probabilities | None required |
| Analyst | + Player composite scores, pipeline metrics | Clerk sign-in |

## Key Constraints

- Prisma ORM for all DB queries — no raw SQL string interpolation
- Clerk middleware protects `/stats` and `/settings` routes
- ML artifacts are offline-generated and seeded into DB; app is read-only
- `DATABASE_URL` and `DIRECT_URL` required for Neon connection pooling
