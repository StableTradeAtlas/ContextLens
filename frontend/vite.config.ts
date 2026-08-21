import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  root: resolve(import.meta.dirname),
  base: "/assets/",
  build: {
    outDir: resolve(import.meta.dirname, "../app/static"),
    emptyOutDir: true,
    assetsDir: "bundles",
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8765" },
  },
});
