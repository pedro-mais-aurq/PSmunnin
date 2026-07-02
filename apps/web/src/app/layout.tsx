import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "LeadHunter AI",
  description: "Sistema multiagente de prospecção B2B",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
