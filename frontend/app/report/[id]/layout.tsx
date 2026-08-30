import type { Metadata } from "next";

import { truncateShareTitle } from "@/lib/shareTitle";
import { SITE_URL } from "@/lib/site";

// 서버(Node.js) 환경에서 실행되므로 절대 URL이 필요하다.
// 로컬: http://localhost:8000
// 프로덕션: NEXT_PUBLIC_API_URL에서 주입 (예: https://cr-check-api.railway.app)
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ReportArticleInfo {
  title?: string;
  publisher?: string;
}

interface ReportApiResponse {
  article_info?: ReportArticleInfo;
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;

  // 기본값 (fetch 실패·404 시 fallback)
  const fallback: Metadata = {
    title: "CR-Check 리포트",
    alternates: { canonical: `/report/${id}` },
    robots: { index: false, follow: true },
  };

  try {
    // 백엔드가 Cache-Control: public, max-age=86400 을 보내지만
    // Next의 fetch 캐시도 명시적으로 1일 revalidate.
    const res = await fetch(`${API_URL}/report/${id}`, {
      next: { revalidate: 86400 },
    });

    if (!res.ok) {
      return fallback;
    }

    const data = (await res.json()) as ReportApiResponse;
    // 브라우저 탭 제목은 원제목, SNS 카드 제목은 축약본을 쓴다.
    const fullTitle = data.article_info?.title || "분석 리포트";
    const shortTitle =
      truncateShareTitle(data.article_info?.title ?? "") || "분석 리포트";
    const publisher = data.article_info?.publisher || "";

    const ogDescription = publisher
      ? `${publisher} 기사에 대한 시민 주도 저널리즘 품질 분석 리포트`
      : "시민 주도 뉴스 품질 분석 리포트";

    return {
      title: `[CR-Check] ${fullTitle}`,
      description: ogDescription,
      alternates: { canonical: `/report/${id}` },
      robots: { index: false, follow: true },
      openGraph: {
        title: shortTitle,
        description: ogDescription,
        type: "article",
        url: `${SITE_URL}/report/${id}`,
        siteName: "CR-Check",
        images: [`${SITE_URL}/og-image.png`],
      },
      twitter: {
        card: "summary",
        title: shortTitle,
        description: ogDescription,
      },
    };
  } catch (e) {
    console.error("generateMetadata fetch failed:", e);
    return fallback;
  }
}

export default function ReportLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
