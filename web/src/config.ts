export const SITE = {
  website: "https://jighog1.github.io/my-auto-blog", // replace this with your deployed domain
  author: "jighog1",
  profile: "https://github.com/jighog1",
  desc: "AI 로봇이 작성하는 최신 트렌드 자동 포스팅 블로그입니다.",
  title: "🤖 AI Tech Blog",
  ogImage: "astropaper-og.jpg",
  lightAndDarkMode: true,
  postPerIndex: 4,
  postPerPage: 6,
  scheduledPostMargin: 15 * 60 * 1000, // 15 minutes
  showArchives: true,
  showBackButton: true, // show back button in post detail
  editPost: {
    enabled: true,
    text: "Edit page",
    url: "https://github.com/jighog1/my-auto-blog/edit/main/web/",
  },
  dynamicOgImage: true,
  dir: "ltr", // "rtl" | "auto"
  lang: "en", // html lang code. Set this empty and default will be "en"
  timezone: "Asia/Bangkok", // Default global timezone (IANA format) https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
} as const;
