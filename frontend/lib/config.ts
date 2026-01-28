export const CONFIG = {
    API_URL: (() => {
        if (process.env.NEXT_PUBLIC_API_URL) {
            return process.env.NEXT_PUBLIC_API_URL;
        }
        // In production, force error if not set (safety)
        // But for now, we follow the original logic which seemed to hardcode the railway URL or localhost
        // We will stick to flexible defaults:
        return 'http://localhost:8000';
    })(),
    ANALYSIS_TIMEOUT: parseInt(process.env.NEXT_PUBLIC_ANALYSIS_TIMEOUT || '300000', 10), // 5 minutes default
} as const;
