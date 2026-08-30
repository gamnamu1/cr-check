import type { MetadataRoute } from "next";

import { SITE_URL } from "@/lib/site";

// 크롤링은 전면 허용한다.
// /report/[id]와 /result의 색인 차단은 각 페이지의 metadata noindex가 맡는다.
// 여기서 disallow를 걸면 크롤러가 페이지를 읽지 못해 그 noindex를 볼 수 없고,
// 오히려 내용 없이 URL만 색인될 수 있다. disallow를 추가하지 말 것.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
