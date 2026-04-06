"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ResultViewer } from "@/components/ResultViewer";
import { CachedBanner } from "@/components/CachedBanner";
import { CONFIG } from "@/lib/config";
import type { AnalysisResult } from "@/types";

type ErrorState = null | "not_found" | "server_error";

export default function ReportPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const shareId = params?.id;

  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ErrorState>(null);

  useEffect(() => {
    if (!shareId) return;

    let cancelled = false;

    const fetchReport = async () => {
      try {
        const res = await fetch(`${CONFIG.API_URL}/report/${shareId}`);
        if (cancelled) return;

        if (res.status === 404) {
          setError("not_found");
          setLoading(false);
          return;
        }
        if (!res.ok) {
          setError("server_error");
          setLoading(false);
          return;
        }
        const data: AnalysisResult = await res.json();
        if (cancelled) return;
        setResult(data);
      } catch (e) {
        if (cancelled) return;
        console.error("Failed to fetch report", e);
        setError("server_error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchReport();
    return () => {
      cancelled = true;
    };
  }, [shareId]);

  const handleReset = () => {
    router.push("/");
  };

  // 로딩 상태
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-navy-800 border-t-transparent rounded-full animate-spin" />
          <p className="text-gray-600 text-sm">리포트를 불러오는 중입니다...</p>
        </div>
      </div>
    );
  }

  // 404
  if (error === "not_found") {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4">
        <h1 className="text-2xl font-bold text-navy-900 mb-3">
          존재하지 않는 리포트입니다
        </h1>
        <p className="text-gray-600 mb-6 text-center">
          요청하신 분석 결과를 찾을 수 없습니다.
          <br />
          링크가 잘못되었거나 삭제되었을 수 있습니다.
        </p>
        <button
          onClick={handleReset}
          className="px-6 py-2.5 bg-navy-800 text-white rounded-md hover:bg-navy-900 transition-colors"
        >
          홈으로 이동
        </button>
      </div>
    );
  }

  // 서버 에러 또는 결과 없음
  if (error === "server_error" || !result) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4">
        <h1 className="text-2xl font-bold text-navy-900 mb-3">
          일시적인 오류입니다
        </h1>
        <p className="text-gray-600 mb-6 text-center">
          잠시 후 다시 시도해주세요.
        </p>
        <button
          onClick={handleReset}
          className="px-6 py-2.5 bg-navy-800 text-white rounded-md hover:bg-navy-900 transition-colors"
        >
          홈으로 이동
        </button>
      </div>
    );
  }

  // 정상 렌더링
  return (
    <>
      {result.analyzed_at && <CachedBanner analyzedAt={result.analyzed_at} />}
      <ResultViewer result={result} onReset={handleReset} />
    </>
  );
}
