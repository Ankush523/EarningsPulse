import type { Metadata } from "next";
import { IBM_Plex_Mono } from "next/font/google";
import Script from "next/script";
import type { ReactNode } from "react";

import { ThemeProvider } from "@/components/ThemeProvider";
import { themeInitScript } from "@/lib/theme";

import "./globals.css";

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
});

const FALLBACK_SITE_URL = "http://localhost:3000";

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? FALLBACK_SITE_URL;

function siteMetadataBase(value: string): URL {
  return URL.canParse(value) ? new URL(value) : new URL(FALLBACK_SITE_URL);
}

export const metadata: Metadata = {
  metadataBase: siteMetadataBase(siteUrl),
  title: {
    default: "EarningsPulse — Pre-Earnings AI Playbooks",
    template: "%s · EarningsPulse",
  },
  description:
    "Know the report. Read the reaction. Watch the ripple. AI-powered pre-earnings research, reaction scenarios, and peer spillover playbooks.",
  keywords: [
    "earnings",
    "AI",
    "finance",
    "playbook",
    "stock research",
    "PRISM",
    "hackathon",
  ],
  authors: [{ name: "EarningsPulse" }],
  openGraph: {
    type: "website",
    locale: "en_US",
    url: siteUrl,
    siteName: "EarningsPulse",
    title: "EarningsPulse — Pre-Earnings AI Playbooks",
    description:
      "AI agent for pre-earnings research, reaction modeling, and peer spillover maps.",
  },
  twitter: {
    card: "summary_large_image",
    title: "EarningsPulse — Pre-Earnings AI Playbooks",
    description: "Know the report. Read the reaction. Watch the ripple.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <Script id="theme-init" strategy="beforeInteractive">
          {themeInitScript}
        </Script>
      </head>
      <body className={`${plexMono.variable} text-ink antialiased`}>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
