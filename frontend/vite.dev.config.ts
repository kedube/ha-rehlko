import { defineConfig } from "vite";

export default defineConfig({
  root: "..",
  cacheDir: "frontend/node_modules/.vite",
  server: {
    host: "127.0.0.1",
  },
});
