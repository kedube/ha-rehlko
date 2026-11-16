import { defineConfig } from "vitest/config";

// The panel ships as one ES module that Home Assistant loads with `panel_custom`: Lit and the
// icon paths are bundled in, and with a single entry and no dynamic imports there is exactly
// one script. It is written straight into the integration's `www/` directory, which the
// sidebar package serves under a content-hashed URL.
//
// The product photos are emitted next to it as files with hashed names, not inlined into the
// script (library mode inlines every asset): a viewer downloads only the photo of their own
// generator, and the script stays a third of the size. A relative `base` makes the script
// find them beside itself, whatever URL it was loaded from.
//
// `www/` holds nothing but this build's output, and is emptied first so that a replaced
// photo leaves no stale copy behind.
export default defineConfig({
  base: "./",
  build: {
    target: "es2022",
    outDir: "../custom_components/rehlko_energy/www",
    emptyOutDir: true,
    sourcemap: false,
    modulePreload: false,
    assetsInlineLimit: 0,
    rolldownOptions: {
      input: "src/rehlko-energy-panel.ts",
      output: {
        format: "es",
        entryFileNames: "rehlko-energy-panel.js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
  test: {
    environment: "happy-dom",
    include: ["test/**/*.test.ts"],
  },
});
