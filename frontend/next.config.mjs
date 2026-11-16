/** @type {import('next').NextConfig} */
let backendUrl =
  process.env.API_URL ||
  process.env.BACKEND_URL ||
  (process.env.NODE_ENV === 'production'
    ? 'https://ares-backend-8xa1.onrender.com'
    : 'http://127.0.0.1:8000');

// Render fromService injects raw hostname (e.g. "ares-backend-8xa1" or "ares-backend.onrender.com").
// Ensure backendUrl is a valid absolute URL for Next.js rewrites:
if (!backendUrl.startsWith('http://') && !backendUrl.startsWith('https://')) {
  if (backendUrl.includes('.onrender.com')) {
    backendUrl = `https://${backendUrl}`;
  } else {
    backendUrl = `https://${backendUrl}.onrender.com`;
  }
}

// Strip any trailing slash to prevent double slashes
backendUrl = backendUrl.replace(/\/+$/, '');

const nextConfig = {
  output: 'standalone',
  eslint: {
    // Avoid blocking production deployments on ESLint checks
    ignoreDuringBuilds: true,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
