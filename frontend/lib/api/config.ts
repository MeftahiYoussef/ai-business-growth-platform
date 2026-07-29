export function backendBaseUrl() {
  const raw = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
  return raw.endsWith('/api') ? raw.slice(0, -4) : raw.replace(/\/$/, '');
}

export function backendApiUrl(path: string) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${backendBaseUrl()}/api${normalizedPath}`;
}
