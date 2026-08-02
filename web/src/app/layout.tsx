import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import Script from "next/script";
import Link from "next/link";
import FeedbackButton from "@/components/FeedbackButton";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Bundestag im O-Ton",
  description: "Neutrale Zusammenfassungen jeder Bundestagsdebatte – mit direkten Zitaten aus dem Protokoll.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="de"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col bg-white dark:bg-zinc-950 pb-16">
        <Script
          id="dark-mode-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark')}}catch(e){}})()`,
          }}
        />
        <main>{children}</main>
        <footer className="fixed bottom-0 left-0 right-0 border-t border-zinc-100 dark:border-zinc-800 bg-white dark:bg-zinc-950 px-4 py-2 text-center z-50">
          <p className="text-xs text-zinc-400">
            Zusammenfassungen und Kurztitel werden KI-generiert und können Fehler enthalten.{" "}
            <Link href="/impressum" className="underline hover:text-zinc-600 dark:hover:text-zinc-300">
              Impressum
            </Link>
            {" · "}
            <Link href="/datenschutz" className="underline hover:text-zinc-600 dark:hover:text-zinc-300">
              Datenschutz
            </Link>
          </p>
        </footer>
        <FeedbackButton />
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
