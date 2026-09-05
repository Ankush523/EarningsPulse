"use client";

import Link from "next/link";

import { BackendStatus } from "@/components/BackendStatus";
import { ThemeToggle } from "@/components/ThemeToggle";

export function HeaderNav() {
  return (
    <nav className="flex items-center gap-2 sm:gap-3">
      <Link href="/calendar" className="link-glass hidden text-[0.95rem] font-medium sm:inline">
        Calendar
      </Link>
      <BackendStatus />
      <ThemeToggle />
    </nav>
  );
}
