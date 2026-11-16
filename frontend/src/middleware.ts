/**
 * Next.js Edge Middleware — route protection for ARES.
 *
 * Checks for the session cookie on every request.
 * Unauthenticated requests to protected routes are redirected to /login.
 *
 * PUBLIC routes (no auth required):
 *   - /login
 *   - /_next/* (Next.js assets)
 *   - /favicon.ico
 *
 * Note: This middleware only checks cookie presence for client-side redirects.
 * The backend independently validates the session on every API call.
 */
import { NextRequest, NextResponse } from 'next/server';

const SESSION_COOKIE = 'ares_session';
const LEGACY_SESSION_COOKIE = 'maar_session';

/** Routes that never require authentication. */
const PUBLIC_PATHS = new Set(['/login', '/ares-logo.png', '/ares-reveal.webm', '/favicon.ico']);

/** Prefixes that are always public (static assets, etc.). */
const PUBLIC_PREFIXES = ['/_next/', '/favicon', '/api/v1/health'];

/** Regex matching any static asset filename with an extension */
const STATIC_ASSET_REGEX = /\.(png|jpe?g|gif|svg|webp|webm|mp4|ico|woff2?|ttf|eot|css|js|map|json|txt|csv|pdf)$/i;

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow static assets, media files, and explicitly public paths
  if (
    PUBLIC_PATHS.has(pathname) ||
    PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix)) ||
    STATIC_ASSET_REGEX.test(pathname)
  ) {
    return NextResponse.next();
  }

  // Development bypass when auto-login is configured
  if (
    process.env.AUTO_LOGIN_DEV === 'true' ||
    process.env.NEXT_PUBLIC_AUTO_LOGIN_DEV === 'true'
  ) {
    return NextResponse.next();
  }

  const session = request.cookies.get(SESSION_COOKIE) || request.cookies.get(LEGACY_SESSION_COOKIE);
  if (!session?.value) {
    // Redirect to login, preserving the original destination
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  /*
   * Match all paths except Next.js internals, static assets, and media files.
   * The pattern below excludes:
   *   - _next/static (static assets)
   *   - _next/image (image optimization)
   *   - favicon.ico
   *   - all static files with extensions (e.g., .png, .webm, .svg, .ico, etc.)
   */
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|webm|mp4|ico|woff2?|ttf|eot|css|js|map|json|txt|csv|pdf)$).*)',
  ],
};
