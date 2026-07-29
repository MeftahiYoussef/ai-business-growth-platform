export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status = 500,
    public readonly details?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function parseApiError(response: Response) {
  try {
    const body = (await response.json()) as { message?: string; details?: unknown };
    return new ApiError(body.message || 'API request failed', response.status, body.details);
  } catch {
    return new ApiError('API request failed', response.status);
  }
}
