import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock Prisma client for unit tests
vi.mock('@/lib/db', () => ({
  prisma: {
    match: {
      findMany: vi.fn(),
      findUnique: vi.fn(),
      count: vi.fn(),
    },
    player: {
      findMany: vi.fn(),
      findUnique: vi.fn(),
    },
    matchPlayer: {
      findMany: vi.fn(),
      findUnique: vi.fn(),
      findFirst: vi.fn(),
    },
    pipelineMetrics: {
      findFirst: vi.fn(),
      findMany: vi.fn(),
    },
  },
}));

// Mock Clerk auth (v7 async API)
vi.mock('@clerk/nextjs/server', () => ({
  auth: vi.fn(async () => ({ userId: null })),
  clerkMiddleware: vi.fn(),
  createRouteMatcher: vi.fn(() => () => false),
  currentUser: vi.fn(async () => null),
}));
