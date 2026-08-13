import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev-mode proxy: the FastAPI server (python -m server.web) listens on 8765.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // The backend admits only its own loopback origin. Vite forwards the
      // browser's :5173 Origin by default, which makes every proxied chat
      // socket fail the backend's fail-closed handshake and look like a server
      // crash. Rewrite only this development proxy hop to its target origin;
      // production continues to use the directly served UI and its native
      // origin without this proxy.
      "/ws": {
        target: "ws://127.0.0.1:8765",
        ws: true,
        configure: (proxy) => {
          proxy.on("proxyReqWs", (proxyRequest) => {
            proxyRequest.setHeader("origin", "http://127.0.0.1:8765");
          });
        },
      },
      "/healthz": { target: "http://127.0.0.1:8765" },
    },
  },
});
