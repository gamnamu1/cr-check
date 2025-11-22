"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";

// 저널리즘 Tip 모음
const JOURNALISM_TIPS = {
  // 문제적 보도 관행 (30개 목표, 현재 10개)
  problematicPractices: [
    "따옴표 저널리즘이란? 취재원의 말을 검증 없이 그대로 인용하여 책임을 회피하는 보도 행태를 말합니다.",
    "무주체 피동형 표현('~로 알려졌다', '~로 전해졌다')은 정보 출처를 숨겨 책임을 회피하는 문제적 표현입니다.",
    "단일 취재원 의존은 균형을 잃게 합니다. 최소 2개 이상의 대립 관점을 취재해야 합니다.",
    "제목의 과장: '[단독]', '[속보]' 남발은 기사의 중요성을 부풀리는 클릭베이트 행태입니다.",
    "익명 취재원 남용: '관계자에 따르면'은 불가피한 경우에만 사용하고, 그 사유를 밝혀야 합니다.",
    "선정적 표현 사용: 극단적이고 자극적인 단어는 갈등을 조장하고 냉정한 판단을 방해합니다.",
    "사실과 의견 혼동: 기자의 주관적 해석을 객관적 사실처럼 전달하면 독자를 오도합니다.",
    "반론권 미보장: 비판 대상에게 해명 기회를 주지 않는 것은 공정성을 해칩니다.",
    "맥락 없는 보도: 배경 설명 없이 사건만 전달하면 독자가 제대로 이해할 수 없습니다.",
    "보도자료 저널리즘: 취재원의 자료를 검증 없이 그대로 옮기는 것은 기자의 역할 포기입니다.",
    // TODO: 20개 추가 예정 (예: 통계 왜곡, 이미지 조작, 제목-본문 불일치 등)
  ],

  // 바람직한 저널리즘 원칙 (15개 목표, 현재 5개)
  principles: [
    "균형 보도: 대립하는 관점을 공정하게 전달하여 독자가 스스로 판단할 수 있게 합니다.",
    "사실 검증: 모든 주장은 최소 2개 이상의 독립적 출처로 확인해야 합니다.",
    "투명성: 취재 과정과 정보원을 가능한 한 투명하게 밝혀야 신뢰를 얻습니다.",
    "권력 감시: 언론의 본질은 권력을 감시하고 비판해 사회 정의를 실현하는 것입니다.",
    "인권 존중: 보도 대상의 인권과 명예를 존중하며, 사생활 침해를 최소화해야 합니다.",
    // TODO: 10개 추가 예정 (예: 독립성, 공익성, 다양성 존중 등)
  ],
};

// 모든 Tip을 하나의 배열로 합치기
const ALL_TIPS = [
  ...JOURNALISM_TIPS.problematicPractices,
  ...JOURNALISM_TIPS.principles,
];

export default function Home() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // 로딩 시작할 때마다 랜덤 Tip 선택
  const randomTip = useMemo(() => {
    return ALL_TIPS[Math.floor(Math.random() * ALL_TIPS.length)];
  }, [isLoading]); // isLoading이 변경될 때마다 새로운 Tip

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!url.trim()) {
      setError("기사 URL을 입력해주세요.");
      return;
    }

    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      setError("올바른 URL 형식이 아닙니다. http:// 또는 https://로 시작해야 합니다.");
      return;
    }

    setIsLoading(true);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 120000); // 120초 타임아웃

      const response = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "서버 오류가 발생했습니다." }));
        throw new Error(errorData.detail || `HTTP ${response.status} 오류`);
      }

      const result = await response.json();

      // 결과를 sessionStorage에 저장
      sessionStorage.setItem("analysisResult", JSON.stringify(result));

      // 결과 페이지로 이동
      router.push("/result");
    } catch (err: any) {
      if (err.name === "AbortError") {
        setError("분석 시간이 2분을 초과했습니다. 다시 시도해주세요.");
      } else {
        setError(err.message || "분석 중 오류가 발생했습니다.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-navy-900 to-navy-700 flex items-center justify-center p-4">
      <div className="max-w-2xl w-full">
        {/* 헤더 */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4 font-serif">
            CR-Check
          </h1>
          <p className="text-amber text-xl font-sans">
            언론윤리 체크 도구
          </p>
        </div>

        {/* 메인 카드 */}
        <div className="card">
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label
                htmlFor="article-url"
                className="block text-navy font-sans font-semibold mb-3 text-lg"
              >
                분석할 기사 URL
              </label>
              <input
                id="article-url"
                type="text"
                className="input-field"
                placeholder="분석할 뉴스 기사의 URL을 입력해주세요..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                disabled={isLoading}
              />
              <p className="text-sm text-gray-600 mt-2 font-sans">
                언론윤리규범 위반이 의심되는 패턴을 찾아 분석합니다.
              </p>
            </div>

            {error && (
              <div className="mb-4 p-4 bg-red-50 border-l-4 border-red-500 text-red-700">
                <p className="font-sans">{error}</p>
              </div>
            )}

            <button
              type="submit"
              className="btn-primary w-full text-lg"
              disabled={isLoading}
            >
              {isLoading ? "분석 중..." : "기사 분석 시작"}
            </button>
          </form>
        </div>

        {/* 설명 */}
        <div className="mt-8 text-center text-white text-sm font-sans opacity-80">
          <p>한국신문윤리위원회 윤리규범을 근거로 기사를 분석합니다.</p>
          <p className="mt-2">분석에는 약 40-60초가 소요됩니다.</p>
        </div>
      </div>

      {/* 로딩 오버레이 */}
      {isLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 max-w-md w-full mx-4">
            <div className="text-center">
              <div className="mb-6">
                <div className="inline-block animate-spin rounded-full h-16 w-16 border-b-4 border-amber"></div>
              </div>
              <h2 className="text-2xl font-bold text-navy mb-4 font-serif">
                기사 분석 중...
              </h2>
              <div className="space-y-3 text-left">
                <div className="flex items-center text-gray-700">
                  <div className="w-2 h-2 bg-amber rounded-full mr-3 animate-pulse"></div>
                  <span className="font-sans">기사 스크래핑 중...</span>
                </div>
                <div className="flex items-center text-gray-700">
                  <div className="w-2 h-2 bg-amber rounded-full mr-3 animate-pulse"></div>
                  <span className="font-sans">Phase 1: 카테고리 식별 중 (5-10초)</span>
                </div>
                <div className="flex items-center text-gray-700">
                  <div className="w-2 h-2 bg-amber rounded-full mr-3 animate-pulse"></div>
                  <span className="font-sans">Phase 2: 3가지 리포트 생성 중 (30-50초)</span>
                </div>
              </div>
              <div className="mt-6 p-4 bg-amber-50 rounded-lg">
                <p className="text-sm text-navy font-sans">
                  💡 Tip: {randomTip}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
