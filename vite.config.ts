import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "./",
  plugins: [react()],
  server: {
    // Honour PORT so a supervising tool can place the dev server on a free
    // port. When it does, bind that exact port instead of drifting to the
    // next free one, or the tool ends up watching a port nothing serves.
    port: Number(process.env.PORT) || 5173,
    strictPort: Boolean(process.env.PORT),
  },
});
