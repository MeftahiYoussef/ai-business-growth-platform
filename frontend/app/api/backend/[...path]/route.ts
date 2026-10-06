import { NextResponse } from 'next/server';
import { backendApiUrl } from '@/lib/api/config';
import { parseApiError } from '@/lib/api/errors';
import { getToken, clearToken } from '@/lib/auth/cookies';

type Params = { params: Promise<{ path: string[] }> };

export function backendProxyPath(path: string[]) {
  return `/${path.join('/')}/`;
}

function passthroughHeaders(response: Response) {
  const headers = new Headers();
  for (const name of ['content-type', 'content-disposition', 'cache-control']) {
    const value = response.headers.get(name);
    if (value) headers.set(name, value);
  }
  return headers;
}

export function isJsonContentType(contentType: string) {
  return contentType.toLowerCase().includes('application/json');
}

async function proxy(request: Request, { params }: Params) {
  const { path } = await params;
  const token = await getToken();
  const url = new URL(request.url);
  const backendUrl = new URL(backendApiUrl(backendProxyPath(path)));
  backendUrl.search = url.search;

  const headers = new Headers(request.headers);
  headers.delete('host');
  headers.delete('cookie');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(backendUrl, {
    method: request.method,
    headers,
    body: ['GET', 'HEAD'].includes(request.method) ? undefined : await request.text(),
    cache: 'no-store'
  });

  if (response.status === 401) {
    await clearToken();
  }

  if (!response.ok) {
    const error = await parseApiError(response);
    return NextResponse.json(
      { success: false, message: error.message, details: error.details },
      { status: error.status }
    );
  }

  const contentType = response.headers.get('content-type') || '';
  if (isJsonContentType(contentType)) {
    const body = await response.json();
    return NextResponse.json(body, { status: response.status });
  }

  return new NextResponse(await response.arrayBuffer(), {
    status: response.status,
    headers: passthroughHeaders(response)
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
