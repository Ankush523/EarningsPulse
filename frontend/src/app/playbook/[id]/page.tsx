import Link from "next/link";

interface PlaybookPageProps {
  params: { id: string };
}

export default function PlaybookPage({ params }: PlaybookPageProps) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-card-border bg-card/50 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent font-mono text-sm font-bold text-white">
              EP
            </div>
            <span className="text-lg font-semibold">EarningsPulse</span>
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-16">
        <h1 className="mb-4 text-3xl font-bold">Playbook</h1>
        <p className="font-mono text-muted">Job ID: {params.id}</p>
        <p className="mt-4 text-muted">
          Playbook viewer and live agent trace will be implemented in Phase 6.
        </p>
        <Link
          href="/"
          className="mt-8 inline-block text-accent hover:underline"
        >
          ← Back to home
        </Link>
      </main>
    </div>
  );
}
