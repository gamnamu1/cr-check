import type { Metadata } from "next";

// 서버(Node.js) 환경에서 실행되므로 절대 URL이 필요하다.
// 로컬: http://localhost:8000
// 프로덕션: NEXT_PUBLIC_API_URL에서 주입 (예: https://cr-check-api.railway.app)
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL || "https://cr-check.vercel.app";

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
  const fallback: Metadata = { title: "CR-Check 리포트" };

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
    const title = data.article_info?.title || "분석 리포트";
    const publisher = data.article_info?.publisher || "";

    const ogTitle = `[CR-Check] ${title}`;
    const ogDescription = publisher
      ? `${publisher} 기사에 대한 시민 주도 저널리즘 품질 분석 리포트`
      : "시민 주도 뉴스 품질 분석 리포트";

    return {
      title: ogTitle,
      description: ogDescription,
      openGraph: {
        title: ogTitle,
        description: "시민 주도 뉴스 품질 분석 리포트",
        type: "article",
        url: `${SITE_URL}/report/${id}`,
        images: [`${SITE_URL}/og-image.png`],
      },
      twitter: {
        card: "summary",
        title: ogTitle,
        description: "시민 주도 뉴스 품질 분석 리포트",
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
