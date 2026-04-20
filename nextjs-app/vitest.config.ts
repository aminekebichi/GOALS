import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'node',
    environmentMatchGlobs: [['__tests__/components/**', 'happy-dom']],
    setupFiles: ['__tests__/setup.ts'],
    globals: true,
    coverage: {
      provider: 'v8',
      thresholds: { lines: 70, functions: 70, branches: 60 },
      exclude: ['e2e/**', 'scripts/**', 'prisma/**', '*.config.*', '.next/**'],
    },
  },
  resolve: {
    alias: { '@': path.resolve(__dirname, '.') },
  },
});
