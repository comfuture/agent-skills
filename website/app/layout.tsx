import type { Metadata } from "next";
import { headers } from "next/headers";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host =
    requestHeaders.get("x-forwarded-host") ??
    requestHeaders.get("host") ??
    "localhost:3000";
  const protocol =
    requestHeaders.get("x-forwarded-proto") ??
    (host.startsWith("localhost") ? "http" : "https");
  const origin = `${protocol}://${host}`;

  return {
    metadataBase: new URL(origin),
    title: {
      default: "Develoop — Close the loop on GitHub work",
      template: "%s — Develoop",
    },
    description:
      "Portable agent skills for creating issues, shipping pull requests, and resolving automated review.",
    openGraph: {
      type: "website",
      url: origin,
      title: "Develoop — Close the loop on GitHub work",
      description:
        "Portable GitHub workflow skills for Codex, Claude Code, Antigravity, and standalone agents.",
      images: [
        {
          url: `${origin}/og.png`,
          width: 1731,
          height: 909,
          alt: "Develoop — Close the loop on GitHub work.",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: "Develoop — Close the loop on GitHub work",
      description:
        "Portable GitHub workflow skills for Codex, Claude Code, Antigravity, and standalone agents.",
      images: [`${origin}/og.png`],
    },
  };
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>
        {children}
      </body>
    </html>
  );
}
