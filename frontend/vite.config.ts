import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, forward API calls to the FastAPI server on port 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/tasks": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
