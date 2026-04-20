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
    pipelineMetrics: {
      findFirst: vi.fn(),
      findMany: vi.fn(),
    },
  },
}));

// Mock Clerk auth
vi.mock('@clerk/nextjs/server', () => ({
  auth: vi.fn(() => ({ userId: null })),
  clerkMiddleware: vi.fn(),
  createRouteMatcher: vi.fn(() => () => false),
  currentUser: vi.fn(() => null),
}));
