import useSWRMutation from 'swr/mutation';
import { CONFIG } from '../config';
import type { AnalysisResult } from '@/types';

interface AnalyzeArgs {
    url: string;
}

async function analyzeArticle(
    url: string,
    { arg }: { arg: AnalyzeArgs }
): Promise<AnalysisResult> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.ANALYSIS_TIMEOUT);

    try {
        const response = await fetch(`${CONFIG.API_URL}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: arg.url }),
            signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            const errorText = await response.text();
            let errorMessage = "서버 오류가 발생했습니다.";

            try {
                const errorJson = JSON.parse(errorText);
                errorMessage = errorJson.detail || errorMessage;
            } catch (e) {
                // Not JSON
                errorMessage = errorText.slice(0, 100) || `HTTP ${response.status}`;
            }

            throw new Error(errorMessage);
        }

        return await response.json();
    } catch (error) {
        clearTimeout(timeoutId);
        throw error;
    }
}

export function useAnalyzeArticle() {
    return useSWRMutation('/api/analyze', analyzeArticle, {
        // Prevent duplicate requests while mutating
        revalidate: false,
    });
}
