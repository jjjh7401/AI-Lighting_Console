import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev-mode proxy: the FastAPI server (python -m server.web) listens on 8765.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/ws": { target: "ws://127.0.0.1:8765", ws: true },
      "/healthz": { target: "http://127.0.0.1:8765" },
    },
  },
});
