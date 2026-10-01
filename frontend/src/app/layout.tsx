import type { Metadata } from "next";
import { IBM_Plex_Mono, Mukta, Noto_Sans_Devanagari, Space_Grotesk } from "next/font/google";
import { DraftBadge } from "@/components/DraftBadge";
import { I18nProvider } from "@/i18n/client";
import { getLocale } from "@/i18n/server";
import "./globals.css";

// Latin fonts are placeholders until the designer confirms the real ones (DESIGN_SYSTEM.md 2.1).
const display = Space_Grotesk({ subsets: ["latin"], variable: "--nf-display", display: "swap" });
const body = Mukta({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--nf-body", display: "swap" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--nf-mono", display: "swap" });
const devanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--nf-devanagari",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "KrishiMitra", template: "%s · KrishiMitra" },
  description: "Preliminary guidance for soybean farmers in Maharashtra.",
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const locale = await getLocale();
  return (
    <html lang={locale} className={`${display.variable} ${body.variable} ${mono.variable} ${devanagari.variable}`}>
      <body>
        <I18nProvider locale={locale}>
          <DraftBadge locale={locale} />
          {children}
        </I18nProvider>
      </body>
    </html>
  );
}
