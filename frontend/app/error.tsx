'use client';

export default function ErrorPage({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <main style={{ padding: 24 }}>
      <div className="app-card">
        <h1>Something went wrong</h1>
        <p>{error.message}</p>
        <button className="button button-primary" onClick={reset}>Try again</button>
      </div>
    </main>
  );
}
