import type { NextConfig } from "next";

const staticExport = process.env.STATIC_EXPORT === "1";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  output: staticExport ? "export" : undefined,
  trailingSlash: true,
  skipTrailingSlashRedirect: true,
  images: {
    formats: ["image/avif", "image/webp"],
    unoptimized: staticExport,
  },
  ...(staticExport ? {} : {
    async rewrites() {
      return [{ source: "/api/:path*", destination: `${process.env.API_PROXY_TARGET || "http://127.0.0.1:8000"}/api/:path*` }];
    },
  }),
};

export default nextConfig;
