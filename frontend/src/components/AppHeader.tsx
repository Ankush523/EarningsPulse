import Link from "next/link";

import { HeaderNav } from "@/components/HeaderNav";

interface AppHeaderProps {
  showNav?: boolean;
}

export function AppHeader({ showNav = true }: AppHeaderProps) {
  return (
    <header className="glass-nav">
      <div className="mx-auto flex max-w-page items-center justify-between px-6 py-4 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5 transition-opacity hover:opacity-80">
          <svg
            width="30"
            height="16"
            viewBox="0 0 30 16"
            fill="none"
            aria-hidden
            className="text-accent"
          >
            <path
              d="M1 9.5H9.5C11.5 9.5 12.3 14 14.5 14C17 14 17.5 6.5 20.5 5.5C23 4.7 26 3 29 3"
              stroke="currentColor"
              strokeWidth="1.75"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="text-[1.2rem] font-semibold leading-none tracking-tight">
            EarningsPulse
          </span>
        </Link>
        {showNav && <HeaderNav />}
      </div>
    </header>
  );
}
