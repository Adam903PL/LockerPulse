import type { Metadata } from "next";
import { Geist_Mono, Montserrat } from "next/font/google";
import "leaflet/dist/leaflet.css";
import "./globals.css";

const montserrat = Montserrat({
  variable: "--font-montserrat",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LockerPulse | AI scoring Paczkomatów",
  description: "InPost-inspired landing i aplikacja do wyboru najlepszego Paczkomatu z historią, zgłoszeniami i triage.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="pl"
      className={`${montserrat.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        {children}
      </body>
    </html>
  );
}
