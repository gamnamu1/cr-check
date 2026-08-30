import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

// 홈 한 건만 포함한다.
// /result는 sessionStorage에 의존하는 임시 화면이라 제외한다.
// /report/[id]는 share_id 목록을 제공하는 백엔드 API가 없을 뿐 아니라,
// 사람의 검수를 거치지 않은 초안을 검색엔진에 유통하지 않는다는 정책에 따라 제외한다.
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: `${SITE_URL}/`,
      lastModified: new Date(),
    },
  ];
}
