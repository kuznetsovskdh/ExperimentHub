import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Прокси на dev-сервере: без него `npm run dev` не видит API, и это ровно те
// грабли, на которых стоит фронтенд РусТеста. Все запросы уходят на /api,
// поэтому CORS в бэкенде не нужен ни в разработке, ни в проде.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 3002,
    proxy: {
      "/api": {
        target: process.env.EH_API_URL || "http://localhost:8001",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
