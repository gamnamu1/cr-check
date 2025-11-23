"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { MainAnalysisCenter } from "@/components/MainAnalysisCenter";
import { AnalysisProcess } from "@/components/AnalysisProcess";
import type { ArticleInput, AnalysisResult } from "@/types";

type AppStatus = "idle" | "analyzing" | "complete";

export default function Home() {
  const router = useRouter();
  const [status, setStatus] = useState<AppStatus>("idle");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async (input: ArticleInput) => {
    setStatus("analyzing");
    setIsLoading(true);
    setError(null);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000); // 300s (5min) timeout

      // Use relative path for API to avoid CORS if proxy is set up, or absolute if needed.
      // The original code used "https://cr-check-production.up.railway.app/analyze"
      // But the plan says "cr-check/backend (FastAPI) ... 백엔드 로직은 유지해야 합니다."
      // And "connect POST /api/analyze".
      // If I am running locally, I should probably use /api/analyze if Next.js rewrites are set up,
      // or the full URL if not.
      // The original code had the full URL. I will stick to it for now, or check next.config.js.
      // Wait, the user request says "cr-check/frontend (Next.js) ... 백엔드(cr-check/backend)는 절대 수정하지 마십시오."
      // I should check if there is a proxy setup in next.config.js.
      // If not, I should use the full URL or localhost if running locally.
      // Given the original code used the production URL, I will use that for now, but ideally it should be configurable.
      // However, for local dev, maybe I should use localhost:8000?
      // The user instructions say "Target Project: Next.js + FastAPI".
      // Usually this implies a local setup.
      // I'll check next.config.js in a separate step if needed, but for now I'll use the production URL as in the original code,
      // BUT I will add a fallback or comment.
      // Actually, better to use the same URL as the original code to be safe, unless I find a reason not to.
      // Original: "https://cr-check-production.up.railway.app/analyze"

      // Bypass Next.js proxy to avoid 30s timeout
      // Backend has CORS enabled for *
      const response = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url: input.content }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const status = response.status;
        const errorText = await response.text();
        console.error(`API Error (${status}):`, errorText);

        let errorMessage = "서버 오류가 발생했습니다.";
        try {
          const errorJson = JSON.parse(errorText);
          errorMessage = errorJson.detail || errorMessage;
          if (typeof errorMessage === 'object') {
            errorMessage = JSON.stringify(errorMessage, null, 2);
          }
        } catch (e) {
          // Not JSON, use text or default
          errorMessage = errorText.slice(0, 100) || `HTTP ${status} 오류`;
        }

        throw new Error(errorMessage);
      }

      const result: AnalysisResult = await response.json();

      // Save to sessionStorage
      sessionStorage.setItem("analysisResult", JSON.stringify(result));

      // Signal AnalysisProcess that loading is done
      setIsLoading(false);
      // Status remains 'analyzing' until AnalysisProcess calls onComplete

    } catch (err: any) {
      console.error(err);
      setStatus("idle");
      setIsLoading(false);
      if (err.name === "AbortError") {
        alert("분석 시간이 5분을 초과했습니다. 다시 시도해주세요.");
      } else {
        alert(err.message || "분석 중 오류가 발생했습니다.");
      }
    }
  };

  const handleAnalysisComplete = () => {
    router.push("/result");
  };

  return (
    <main>
      {status === "idle" && (
        <MainAnalysisCenter onAnalyze={handleAnalyze} />
      )}

      {status === "analyzing" && (
        <AnalysisProcess
          isLoading={isLoading}
          onComplete={handleAnalysisComplete}
        />
      )}
    </main>
  );
}

