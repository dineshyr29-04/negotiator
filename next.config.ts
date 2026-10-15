import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!backendUrl) return [];
    return [
      { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
      { source: "/static/:path*", destination: `${backendUrl}/static/:path*` },
    ];
  },
};

export default nextConfig;
