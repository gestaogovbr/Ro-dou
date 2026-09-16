import { defineConfig } from "vite";

const backendUrl = process.env.RO_DOU_CHAT_BACKEND_URL ?? "http://127.0.0.1:8001";
const apiToken = process.env.RO_DOU_CHAT_API_TOKEN ?? "";

export default defineConfig({
  server: {
    proxy: {
      "/api": {
        target: backendUrl,
        changeOrigin: true,
        configure(proxy) {
          proxy.on("proxyReq", (proxyRequest) => {
            if (apiToken) {
              proxyRequest.setHeader("Authorization", `Bearer ${apiToken}`);
            }
          });
        },
      },
    },
  },
});
