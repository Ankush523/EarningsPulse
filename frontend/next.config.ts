import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const configDir = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  // Docker copies `.next/standalone`. Vercel injects its own adapter and
  // ignores that directory; Next 16.3 plus standalone fails onBuildComplete.
  output: process.env.VERCEL ? undefined : "standalone",
  reactCompiler: true,
  turbopack: {
    root: configDir,
  },
};

export default nextConfig;
