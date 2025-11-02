import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "The Unexpected Trader | Dashboard",
  description: "Live trading dashboard powered by Aster API and Coinglass Data",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
