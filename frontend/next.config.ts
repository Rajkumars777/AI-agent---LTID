import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',  // Static export for Tauri desktop
  images: { unoptimized: true }, // Required for static export
  reactCompiler: true,
};

export default nextConfig;
