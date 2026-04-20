import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Prisma generates in node_modules — needed for Edge-compatible builds
  serverExternalPackages: ['@prisma/client'],
};

export default nextConfig;
