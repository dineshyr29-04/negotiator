import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Proxy /api/* and /ws/* to the Python backend when NEXT_PUBLIC_API_URL is set
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
