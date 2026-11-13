import { defineConfig } from "vitest/config";

// The panel ships as one self-contained ES module that Home Assistant loads with
// `panel_custom` — Lit and the icon paths are bundled in, and with a single entry and no
// dynamic imports Vite's library mode already emits exactly one file. It is written straight
// into the integration's `www/` directory, where the sidebar package serves it with a
// content-hashed URL.
export default defineConfig({
  build: {
    target: "es2022",
    outDir: "../custom_components/rehlko_energy/www",
    emptyOutDir: false,
    sourcemap: false,
    lib: {
      entry: "src/rehlko-energy-panel.ts",
      formats: ["es"],
      fileName: () => "rehlko-energy-panel.js",
    },
  },
  test: {
    environment: "happy-dom",
    include: ["test/**/*.test.ts"],
  },
});
