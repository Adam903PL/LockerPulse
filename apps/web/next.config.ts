import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "static.easypack24.net",
        pathname: "/points/**",
      },
    ],
  },
};

export default nextConfig;
