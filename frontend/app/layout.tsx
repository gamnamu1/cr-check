import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CR-Check - 언론윤리 체크 도구",
  description: "한국신문윤리위원회 윤리규범 기반 기사 분석 도구",
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
