import { defineConfig } from "vite";

export default defineConfig({
  server: {
    host: "127.0.0.1",
    port: 4173,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    css: false,
  },
});
