import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  server: {
    host: "127.0.0.1",
    port: 44731,
    strictPort: true,
    proxy: {
      "/ws": { target: "http://127.0.0.1:44732", ws: true },
      "/api": "http://127.0.0.1:44732",
    },
  },
});
