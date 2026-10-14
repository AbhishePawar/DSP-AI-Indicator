import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  // Keep automatic JSX for Vitest while bypassing the newer Vite config type
  // omission for esbuild's JSX option. Runtime behavior is covered by the test suite.
  esbuild: {
    jsx: "automatic",
  } as never,
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    setupFiles: ["./vitest.setup.ts"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
