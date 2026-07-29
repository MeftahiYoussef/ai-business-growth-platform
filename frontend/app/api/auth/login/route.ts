import { NextResponse } from 'next/server';
import { backendApiUrl } from '@/lib/api/config';
import { parseApiError } from '@/lib/api/errors';
import { setToken } from '@/lib/auth/cookies';
import type { ApiEnvelope, User } from '@/types/api';

export async function POST(request: Request) {
  const response = await fetch(backendApiUrl('/auth/login'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(await request.json())
  });

  if (!response.ok) {
    const error = await parseApiError(response);
    return NextResponse.json({ message: error.message, details: error.details }, { status: error.status });
  }

  const body = (await response.json()) as ApiEnvelope<User>;
  if (body.token) await setToken(body.token);
  return NextResponse.json({ success: true, data: body.data });
}
