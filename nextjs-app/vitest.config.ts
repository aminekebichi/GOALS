import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "node",
    exclude: ["node_modules", "e2e/**", ".next/**"],
    environmentMatchGlobs: [["__tests__/components/**", "happy-dom"]],
    setupFiles: ["__tests__/setup.ts"],
    globals: true,
    coverage: {
      provider: "v8",
      thresholds: { lines: 70, functions: 70, branches: 60 },
      // Server components (page.tsx) and UI components require E2E testing, not unit tests
      exclude: [
        "e2e/**",
        "scripts/**",
        "prisma/**",
        "*.config.*",
        ".next/**",
        "app/**/page.tsx",
        "app/**/layout.tsx",
        "components/**",
        "lib/**",
        "proxy.ts",
      ],
    },
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, ".") },
  },
});
