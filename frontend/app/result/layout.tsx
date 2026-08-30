import type { Metadata } from "next";

// result/page.tsx는 "use client" 컴포넌트라 그 파일에서 metadata를 export할 수 없다.
// 색인 제외를 선언하려면 서버 컴포넌트인 layout이 필요해 이 파일을 따로 둔다.
// 마크업이 없다고 지우면 /result가 검색 결과에 노출되므로 유지할 것.
export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export default function ResultLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
