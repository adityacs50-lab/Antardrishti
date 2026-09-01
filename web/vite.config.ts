import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// prahari web — served locally only. No CDN, no external fonts, no analytics.
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: {
    host: true,
    port: 5173,
    proxy: {
      // Dev convenience: same-origin /api so nothing needs CORS or a base URL.
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/health": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  build: { outDir: "dist", sourcemap: false },
});
