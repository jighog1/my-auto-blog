export const SITE = {
  website: "https://fivejh.com", // replace this with your deployed domain
  author: "Tech Insights Desk",
  profile: "https://github.com/jighog1",
  desc: "전문가의 심층 분석이 담긴 최신 IT/AI 트렌드 미디어 플랫폼입니다.",
  title: "Tech Insights Desk",
  ogImage: "astropaper-og.jpg",
  lightAndDarkMode: true,
  postPerIndex: 4,
  postPerPage: 6,
  scheduledPostMargin: 15 * 60 * 1000, // 15 minutes
  showArchives: true,
  showBackButton: true, // show back button in post detail
  editPost: {
    enabled: false,
    text: "Edit page",
    url: "https://github.com/jighog1/my-auto-blog/edit/main/web/",
  },
  dynamicOgImage: true,
  dir: "ltr", // "rtl" | "auto"
  lang: "en", // html lang code. Set this empty and default will be "en"
  timezone: "Asia/Bangkok", // Default global timezone (IANA format) https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
} as const;
