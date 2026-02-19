import type { Metadata } from "next";
import { Outfit, Geist_Mono } from "next/font/google";
import "./globals.css";

const outfit = Outfit({
  variable: "--font-outfit",
  subsets: ["latin"],
  weight: ["300", "400", "500", "700", "900"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Nexus | Next-Gen AI Agent",
  description: "Experience the power of an intelligent workflow automation system. Powered by advanced autonomous reasoning.",
};

import TauriProvider from "@/components/TauriProvider";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${outfit.variable} ${geistMono.variable} antialiased selection:text-white`}
      >
        <TauriProvider>
          {children}
        </TauriProvider>
      </body>
    </html>
  );
}
