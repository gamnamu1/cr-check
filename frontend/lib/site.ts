/**
 * 사이트 URL의 단일 진실 공급원.
 *
 * NEXT_PUBLIC_SITE_URL이 비어 있거나 형식이 잘못돼도 정식 도메인이 유지되도록
 * DEFAULT_SITE_URL로 fallback한다.
 */

export const DEFAULT_SITE_URL = "https://cr-check.kr";

/**
 * 환경변수 값에서 오리진(스킴·호스트·포트)만 남긴다.
 * URL 파서의 .origin을 쓰므로 끝 슬래시뿐 아니라 경로·쿼리·해시도 함께 버려진다.
 */
function normalizeOrigin(raw: string | null | undefined): string | null {
  const value = raw?.trim();
  if (!value) return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return null;
    }
    return url.origin;
  } catch {
    return null;
  }
}

// Next.js의 빌드 시 인라인 치환이 동작하도록 process.env.NEXT_PUBLIC_SITE_URL을 직접 참조한다.
export const SITE_URL =
  normalizeOrigin(process.env.NEXT_PUBLIC_SITE_URL) ?? DEFAULT_SITE_URL;
