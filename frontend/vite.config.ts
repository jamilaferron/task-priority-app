import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development, forward API calls to the FastAPI server on port 8000.
const API_PATHS = ["/tasks", "/schedule", "/checklist", "/routines", "/events", "/calendars", "/periods", "/health"];

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: Object.fromEntries(API_PATHS.map((path) => [path, "http://localhost:8000"])),
  },
});
