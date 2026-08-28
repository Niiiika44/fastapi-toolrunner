import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// In production the SPA is served by the same nginx that proxies the API, so a
// relative `/api` base needs no proxying at all. In dev Vite plays the part of
// that nginx: it forwards `/api` (HTTP and WebSocket alike) to the backend
// without rewriting the path, exactly like `location /api/` does in
// deploy/nginx/nginx.conf. FastAPI runs with root_path=/api, so it accepts the
// prefixed path as is.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.VITE_DEV_API_TARGET ?? "http://127.0.0.1:8000";

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        "/api": { target, changeOrigin: true, ws: true },
      },
    },
    build: { outDir: "dist", sourcemap: true },
  };
});
