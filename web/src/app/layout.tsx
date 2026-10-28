import type { Metadata } from "next";
import { Geist, Geist_Mono, Jost, Space_Grotesk } from "next/font/google";
import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import Script from "next/script";
import FeedbackButton from "@/components/FeedbackButton";
import MailOutageNotice from "@/components/MailOutageNotice";
import SiteFooter from "@/components/SiteFooter";
import PdfSplitScreenProvider from "@/components/PdfSplitScreenProvider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const jost = Jost({
  variable: "--font-jost",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
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
      className={`${geistSans.variable} ${geistMono.variable} ${jost.variable} ${spaceGrotesk.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col bg-white dark:bg-zinc-950 md:pb-16">
        <Script
          id="dark-mode-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('theme');if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme: dark)').matches)){document.documentElement.classList.add('dark')}}catch(e){}})()`,
          }}
        />
        <PdfSplitScreenProvider>
          <MailOutageNotice />
          <main>{children}</main>
          <SiteFooter />
          <FeedbackButton />
        </PdfSplitScreenProvider>
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
