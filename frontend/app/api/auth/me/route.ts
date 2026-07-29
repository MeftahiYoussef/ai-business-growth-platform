import { NextResponse } from 'next/server';
import { serverApi } from '@/lib/api/server';
import { clearToken } from '@/lib/auth/cookies';
import type { ApiEnvelope, Business, User } from '@/types/api';

export async function GET() {
  try {
    const user = await serverApi<ApiEnvelope<User>>('/auth/me');
    const business = await serverApi<ApiEnvelope<Business | null>>('/business/me').catch(() => ({
      success: true,
      data: null
    }));
    return NextResponse.json({
      success: true,
      data: user.data,
      hasBusiness: Boolean(business.data)
    });
  } catch (error) {
    await clearToken();
    const message = error instanceof Error ? error.message : 'Authentication failed';
    return NextResponse.json({ message }, { status: 401 });
  }
}
