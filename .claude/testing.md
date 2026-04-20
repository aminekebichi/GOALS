# Testing Strategy

## Principles

- **TDD red-green-refactor** for all new features: commit failing tests before implementation
- Assert **behavior**, not implementation details
- Mock at system boundaries (Prisma, Clerk) — never mock internals
- 70%+ line coverage enforced in CI

## Test Pyramid

```
         /\
        /E2E\        Playwright — 2 specs minimum
       /------\
      / Integr \     Vitest — API routes with mocked Prisma
     /----------\
    /    Unit    \   Vitest — components, utilities, pure functions
   /______________\
```

## Tool Config

| Tool | Config file | Environment |
|------|-------------|-------------|
| Vitest 3 | `vitest.config.ts` | `node` for API tests, `happy-dom` for components |
| Playwright | `playwright.config.ts` | Chromium headless |
| Coverage | `@vitest/coverage-v8` | Threshold: 70% lines/functions, 60% branches |

## TDD Git Pattern

Each feature must show this commit sequence:

```
feat: add failing tests for [feature]   ← RED (tests fail, no implementation)
feat: implement [feature]               ← GREEN (tests pass)
refactor: [optional cleanup]            ← REFACTOR
```

## Test Locations

```
nextjs-app/
├── __tests__/
│   ├── setup.ts              # Global mocks (Prisma, Clerk)
│   ├── api/                  # Route handler tests
│   └── components/           # React component tests
└── e2e/                      # Playwright E2E specs
```

## What to Test

- API routes: status codes, response shapes, auth enforcement, query param filtering
- Components: renders correctly, user interactions, edge cases (empty state, loading)
- E2E: critical user flows — match calendar loads, auth redirect, protected page access
