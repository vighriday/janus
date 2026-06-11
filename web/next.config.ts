import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The console is a standalone Next server (deployed as its own container app);
  // the browser talks to the FastAPI backend directly over SSE.
  output: "standalone",
  reactStrictMode: true,
};

export default nextConfig;
