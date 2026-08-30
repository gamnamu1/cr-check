import type { Metadata } from "next";
import "./globals.css";

import { SITE_URL } from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: "CR-Check - 언론윤리 체크 도구",
  description: "한국신문윤리위원회 윤리규범 기반 기사 분석 도구",
  alternates: { canonical: "/" },
  openGraph: {
    title: "CR-Check - 언론윤리 체크 도구",
    description: "한국신문윤리위원회 윤리규범 기반 기사 분석 도구",
    url: "/",
    siteName: "CR-Check",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
