"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ResultViewer } from "@/components/ResultViewer";
import type { AnalysisResult } from "@/types";

export default function ResultPage() {
  const router = useRouter();
  const [result, setResult] = useState<AnalysisResult | null>(null);

  useEffect(() => {
    // Load result from sessionStorage
    const savedResult = sessionStorage.getItem("analysisResult");
    if (savedResult) {
      try {
        setResult(JSON.parse(savedResult));
      } catch (e) {
        console.error("Failed to parse result", e);
        router.push("/");
      }
    } else {
      // No result found, redirect to home
      router.push("/");
    }
  }, [router]);

  const handleReset = () => {
    sessionStorage.removeItem("analysisResult");
    router.push("/");
  };

  if (!result) {
    return null; // Or a loading spinner
  }

  return <ResultViewer result={result} onReset={handleReset} />;
}
