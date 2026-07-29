import { cookies } from 'next/headers';

export const authCookieName = 'ai_growth_token';

export async function getToken() {
  return (await cookies()).get(authCookieName)?.value;
}

export async function setToken(token: string) {
  (await cookies()).set(authCookieName, token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: 60 * 60 * 24 * 7
  });
}

export async function clearToken() {
  (await cookies()).delete(authCookieName);
}
