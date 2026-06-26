import { defineConfig } from "vitest/config";
import viteReact from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [viteReact()],
  test: {
    passWithNoTests: true,
    environment: "jsdom",
    globals: true,
  },
});
