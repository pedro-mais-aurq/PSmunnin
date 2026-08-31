import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PS Munnin",
  description:
    "Painel de prospecção B2B para leads com baixa maturidade digital",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
