"use client";

interface CachedBannerProps {
  analyzedAt: string;
}

function formatKoreanDate(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("ko-KR", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

export function CachedBanner({ analyzedAt }: CachedBannerProps) {
  return (
    <div className="bg-gray-100 border-b border-gray-200 px-4 py-2.5 text-center">
      <p className="text-xs text-gray-600 font-light">
        이 기사는 {formatKoreanDate(analyzedAt)}에 분석된 결과입니다.
      </p>
    </div>
  );
}
