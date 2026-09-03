import Link from "next/link";

import { BackendStatus } from "@/components/BackendStatus";

interface AppHeaderProps {
  showNav?: boolean;
}

export function AppHeader({ showNav = true }: AppHeaderProps) {
  return (
    <header className="sticky top-0 z-50 border-b border-card-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent font-mono text-sm font-bold text-white">
            EP
          </div>
          <span className="text-lg font-semibold tracking-tight">
            EarningsPulse
          </span>
        </Link>
        {showNav && (
          <nav className="flex items-center gap-6 text-sm text-muted">
            <Link href="/calendar" className="transition hover:text-foreground">
              Calendar
            </Link>
            <BackendStatus />
          </nav>
        )}
      </div>
    </header>
  );
}
