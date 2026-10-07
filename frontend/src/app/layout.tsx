import type { Metadata } from "next";
import { Bricolage_Grotesque, Hind } from "next/font/google";
import "./globals.css";

const bricolageGrotesque = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--font-bricolage",
  display: "swap",
});

const hind = Hind({
  weight: ["400", "500", "600", "700"],
  subsets: ["latin", "devanagari"],
  variable: "--font-hind",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Udaan — Careers your whole family can agree on",
  description: "Career guidance for the whole family. Find careers both student and parent agree on.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${bricolageGrotesque.variable} ${hind.variable}`}
    >
      <body className="min-h-screen bg-paper text-midnight antialiased">
        {children}
      </body>
    </html>
  );
}
