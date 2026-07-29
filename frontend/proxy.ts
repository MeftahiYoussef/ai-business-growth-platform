import { NextResponse, type NextRequest } from 'next/server';
import { authCookieName } from './lib/auth/cookies';

const publicPaths = ['/login', '/register', '/forgot-password'];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get(authCookieName)?.value;
  const isPublic = publicPaths.some((path) => pathname === path);
  const isProtected =
    pathname === '/' ||
    pathname.startsWith('/dashboard') ||
    pathname.startsWith('/onboarding') ||
    pathname.startsWith('/competitors') ||
    pathname.startsWith('/trends') ||
    pathname.startsWith('/generate') ||
    pathname.startsWith('/studio') ||
    pathname.startsWith('/calendar') ||
    pathname.startsWith('/analytics') ||
    pathname.startsWith('/integrations') ||
    pathname.startsWith('/team') ||
    pathname.startsWith('/reports') ||
    pathname.startsWith('/notifications') ||
    pathname.startsWith('/strategy') ||
    pathname.startsWith('/analysis') ||
    pathname.startsWith('/profile') ||
    pathname.startsWith('/settings');

  if (!token && isProtected) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  if (token && isPublic) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|icons).*)']
};
