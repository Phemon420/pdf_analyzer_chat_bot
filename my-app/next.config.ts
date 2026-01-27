import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
  webpack: (config) => {
    // 1. Fix for the "Object.defineProperty" crash
    // This tells Webpack to treat .mjs files in node_modules as standard JS
    // preventing the buggy HMR transformation
    config.module.rules.push({
      test: /\.mjs$/,
      include: /node_modules/,
      type: 'javascript/auto',
    });

    // 2. Fix for the 'canvas' module not found error
    config.resolve.alias = {
      ...config.resolve.alias,
      canvas: false,
    };

    config.resolve.fallback = {
      ...config.resolve.fallback,
      canvas: false,
    };

    return config;
  }
};

export default nextConfig;