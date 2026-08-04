// CommonJS avoids Vite's ESM-in-CommonJS config warning without changing the app package type.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const path = require("node:path");

const config = {
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: false,
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./src/test/setup.ts"],
  },
} satisfies import("vitest/config").ViteUserConfigExport;

module.exports = config;
