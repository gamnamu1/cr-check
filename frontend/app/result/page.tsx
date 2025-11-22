"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import React from "react";

interface AnalysisResult {
  article_info: {
    title: string;
    url: string;
  };
  reports: {
    comprehensive: string;
    journalist: string;
    student: string;
  };
}

type ReportType = "comprehensive" | "journalist" | "student";

const REPORT_TABS = [
  {
    key: "comprehensive" as ReportType,
    label: "시민을 위한 종합 리포트",
    icon: "📂",
    description: "일반 독자가 이해하기 쉬운 언어",
  },
  {
    key: "journalist" as ReportType,
    label: "기자를 위한 전문 리포트",
    icon: "📂",
    description: "윤리 규범 근거와 구체적 대안 제시",
  },
  {
    key: "student" as ReportType,
    label: "학생을 위한 교육 리포트",
    icon: "📂",
    description: "문답식 교육 자료",
  },
];

// 윤리규범 인용 하이라이팅 함수
function highlightEthicsCitations(text: string): React.ReactNode[] {
  // 윤리규범 패턴들
  const patterns = [
    /언론윤리헌장\s*제\s*\d+조[^.\n]*/g,
    /신문윤리실천요강\s*제\s*\d+조[^.\n]*/g,
    /기자윤리실천요강\s*\d+-\d+\)[^.\n]*/g,
    /한국기자협회\s*윤리강령\s*제\s*\d+조[^.\n]*/g,
  ];

  // 모든 패턴을 하나의 정규식으로 결합
  const combinedPattern = new RegExp(
    patterns.map(p => p.source).join('|'),
    'g'
  );

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match;

  while ((match = combinedPattern.exec(text)) !== null) {
    // 매칭 전 텍스트
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    // 윤리규범 인용 (스타일 적용)
    parts.push(
      <span key={match.index} className="ethics-citation">
        {match[0]}
      </span>
    );

    lastIndex = match.index + match[0].length;
  }

  // 남은 텍스트
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}

export default function ResultPage() {
  const router = useRouter();
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [activeTab, setActiveTab] = useState<ReportType>("comprehensive");
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    const storedResult = sessionStorage.getItem("analysisResult");
    if (!storedResult) {
      router.push("/");
      return;
    }

    try {
      const parsed = JSON.parse(storedResult);
      setResult(parsed);
    } catch (err) {
      console.error("Failed to parse result:", err);
      router.push("/");
    }
  }, [router]);

  const handleExportPDF = async () => {
    if (!result) return;

    setIsExporting(true);

    try {
      const response = await fetch("https://cr-check-production.up.railway.app/export-pdf", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(result),
      });

      if (!response.ok) {
        throw new Error("PDF 생성에 실패했습니다.");
      }

      // PDF 다운로드
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `CR-Check_${result.article_info.title.slice(0, 30)}_${new Date().toISOString().slice(0, 10)}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error: any) {
      alert(error.message || "PDF 생성 중 오류가 발생했습니다.");
    } finally {
      setIsExporting(false);
    }
  };

  if (!result) {
    return (
      <div className="min-h-screen bg-navy-900 flex items-center justify-center">
        <div className="text-white text-xl font-sans">로딩 중...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-navy-900 to-navy-700 py-12 px-4">
      <div className="max-w-5xl mx-auto">
        {/* 헤더 */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2 font-serif">
            분석 결과
          </h1>
          <p className="text-amber text-lg font-sans">
            Analysis Report
          </p>
        </div>

        {/* 기사 정보 카드 */}
        <div className="card mb-8">
          <h2 className="text-2xl font-bold text-navy mb-4 font-serif">
            📰 기사 정보
          </h2>
          <div className="space-y-3">
            <div>
              <p className="text-sm font-sans font-semibold text-gray-600 mb-1">
                제목
              </p>
              <p className="text-lg text-gray-900">
                {result.article_info.title}
              </p>
            </div>
            <div>
              <p className="text-sm font-sans font-semibold text-gray-600 mb-1">
                URL
              </p>
              <a
                href={result.article_info.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-amber hover:underline break-all font-sans"
              >
                {result.article_info.url}
              </a>
            </div>
          </div>
        </div>

        {/* 리포트 탭 */}
        <div className="card mb-8">
          <h2 className="text-2xl font-bold text-navy mb-6 font-serif">
            📊 평가 리포트
          </h2>

          {/* 탭 헤더 */}
          <div className="flex flex-col sm:flex-row gap-2 mb-6">
            {REPORT_TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex-1 px-4 py-3 rounded-lg font-sans font-semibold transition-all ${
                  activeTab === tab.key
                    ? "bg-navy text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                <div className="flex items-center justify-center gap-2">
                  <span>{tab.icon}</span>
                  <span className="text-sm">{tab.label.split(" ")[0]}</span>
                </div>
              </button>
            ))}
          </div>

          {/* 탭 설명 */}
          <div className="mb-4 p-4 bg-amber-50 rounded-lg border-l-4 border-amber">
            <p className="text-sm font-sans text-navy">
              {REPORT_TABS.find((tab) => tab.key === activeTab)?.description}
            </p>
          </div>

          {/* 리포트 내용 */}
          <div className="bg-gray-50 rounded-lg p-6">
            <div className="prose max-w-none">
              <div className="whitespace-pre-wrap text-gray-900 leading-relaxed">
                {highlightEthicsCitations(result.reports[activeTab])}
              </div>
            </div>
          </div>
        </div>

        {/* 액션 바 */}
        <div className="card sticky bottom-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <button
              onClick={handleExportPDF}
              className="btn-secondary flex-1"
              disabled={isExporting}
            >
              {isExporting ? "📄 PDF 생성 중..." : "📄 PDF로 결과 저장"}
            </button>
            <button
              onClick={() => router.push("/")}
              className="btn-primary flex-1"
            >
              🔍 다른 기사 분석하기
            </button>
          </div>
        </div>

        {/* 푸터 */}
        <div className="mt-8 text-center text-white text-sm font-sans opacity-60">
          <p>Powered by CR-Check Analysis Engine</p>
          <p className="mt-1">한국신문윤리위원회 윤리규범 기반</p>
        </div>
      </div>
    </div>
  );
}
