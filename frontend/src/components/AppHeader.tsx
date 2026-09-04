import Link from "next/link";

import { BackendStatus } from "@/components/BackendStatus";

interface AppHeaderProps {
  showNav?: boolean;
}

export function AppHeader({ showNav = true }: AppHeaderProps) {
  return (
    <header className="border-b border-rule">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Link href="/" className="flex items-center gap-2.5">
          <svg
            width="30"
            height="16"
            viewBox="0 0 30 16"
            fill="none"
            aria-hidden
            className="text-ink"
          >
            <path
              d="M1 9.5H9.5C11.5 9.5 12.3 14 14.5 14C17 14 17.5 6.5 20.5 5.5C23 4.7 26 3 29 3"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="text-[1.35rem] font-medium leading-none tracking-tight">
            EarningsPulse
          </span>
        </Link>
        {showNav && (
          <nav className="flex items-center gap-5 text-[0.95rem] sm:gap-7">
            <Link
              href="/calendar"
              className="text-ink-soft underline-offset-4 transition hover:text-ink hover:underline"
            >
              Calendar
            </Link>
            <BackendStatus />
          </nav>
        )}
      </div>
    </header>
  );
}
