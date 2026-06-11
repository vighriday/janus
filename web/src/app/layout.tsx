import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JANUS",
  description: "A decision guardrail for autonomous enterprise agents.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
