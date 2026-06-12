import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JANUS — decision guardrail",
  description:
    "A decision guardrail for autonomous enterprise agents. It intercepts a proposed action, retrieves analogous past decisions with Foundry IQ, and pauses for human approval.",
  icons: { icon: "/icon.svg" },
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
