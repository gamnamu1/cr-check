"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { MainAnalysisCenter } from "@/components/MainAnalysisCenter";
import { AnalysisProcess } from "@/components/AnalysisProcess";
import { useAnalyzeArticle } from "@/lib/api/analyze";
import type { ArticleInput, AnalysisResult } from "@/types";

type AppStatus = "idle" | "analyzing" | "complete";

export default function Home() {
  const router = useRouter();
  const [status, setStatus] = useState<AppStatus>("idle");
  // useSWRMutation hook handles loading state and execution
  const { trigger, isMutating, error: swrError } = useAnalyzeArticle();

  const handleAnalyze = async (input: ArticleInput) => {
    setStatus("analyzing");

    try {
      // Trigger the mutation (request)
      const result = await trigger({ url: input.content });

      // Save to sessionStorage
      sessionStorage.setItem("analysisResult", JSON.stringify(result));

      // Note: We don't change status to 'complete' here instantly.
      // The AnalysisProcess component handles the transition to 'complete'
      // and calls onComplete when it's done with its internal timer/animation.

    } catch (err: any) {
      console.error(err);
      setStatus("idle");

      const errorMessage = err?.message || "분석 중 오류가 발생했습니다.";

      if (err?.name === "AbortError") {
        alert("분석 시간이 5분을 초과했습니다. 다시 시도해주세요.");
      } else {
        alert(errorMessage);
      }
    }
  };

  const handleAnalysisComplete = useCallback(() => {
    router.push("/result");
  }, [router]);

  return (
    <main>
      {status === "idle" ? (
        <MainAnalysisCenter onAnalyze={handleAnalyze} />
      ) : null}

      {status === "analyzing" ? (
        <AnalysisProcess
          isLoading={isMutating}
          onComplete={handleAnalysisComplete}
        />
      ) : null}
    </main>
  );
}

