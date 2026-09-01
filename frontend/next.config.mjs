/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  transpilePackages: ["@cstf/core"],
  async rewrites() {
    return process.env.BACKEND_URL ? [{ source: "/api/:path*", destination: `${process.env.BACKEND_URL}/api/:path*` }] : [];
  },
};
export default nextConfig;
