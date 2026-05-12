import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function proxy(request: NextRequest) {
  const token = request.cookies.get('kuaai_token')?.value
  const { pathname } = request.nextUrl

  const isLoginPage = pathname === '/login'
  const isDashboard = pathname.startsWith('/dashboard') ||
    pathname.startsWith('/employees') ||
    pathname.startsWith('/documents') ||
    pathname.startsWith('/chat')

  if (!token && isDashboard) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  if (token && isLoginPage) {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  if (token && pathname === '/') {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
