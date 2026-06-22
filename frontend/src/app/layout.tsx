import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Acreva HireFlow — AI Recruitment Assistant",
  description: "From CV to shortlist to interview. AI-assisted screening for recruiters.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
