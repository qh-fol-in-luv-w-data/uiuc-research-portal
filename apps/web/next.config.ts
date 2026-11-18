import type { NextConfig } from "next";

// The browser only ever talks to this Next.js server; /api/* and /health are proxied to FastAPI by
// route handlers (src/app/api/[...path], src/app/health) that read API_URL at request time.

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  productionBrowserSourceMaps: false,
  poweredByHeader: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  images: {
    remotePatterns: [{ protocol: "https", hostname: "upload.wikimedia.org" }],
  },
};

export default nextConfig;
