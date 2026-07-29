import Link from 'next/link';

export default function NotFound() {
  return (
    <main style={{ padding: 24 }}>
      <div className="app-card">
        <h1>Page not found</h1>
        <Link className="button button-primary" href="/dashboard">Back to dashboard</Link>
      </div>
    </main>
  );
}
