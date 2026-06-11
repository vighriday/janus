import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export keeps the frontend a plain static bundle for the demo; the
  // browser talks to the FastAPI backend directly over SSE.
  reactStrictMode: true,
};

export default nextConfig;
