import type { CollectionEntry } from "astro:content";

type BlogPost = CollectionEntry<"blog">;

const WORK_SIGNAL_GROUPS = [
  {
    weight: 10,
    signals: ["업무자동화", "업무생산성", "업무 활용", "업무 적용"],
  },
  {
    weight: 8,
    signals: [
      "실무 적용",
      "워크플로",
      "workflow",
      "생산성",
      "productivity",
      "자동화",
      "automation",
    ],
  },
  {
    weight: 7,
    signals: ["협업", "collaboration", "조직", "enterprise"],
  },
  {
    weight: 6,
    signals: [
      "보고서",
      "문서",
      "회의",
      "리서치",
      "마케팅",
      "고객",
      "콘텐츠 제작",
    ],
  },
  { weight: 4, signals: ["개발 생산성", "코딩", "보안"] },
] as const;

const normalize = (value: string) => value.toLocaleLowerCase("ko-KR");

export const getWorkRelevanceScore = ({ data }: BlogPost) => {
  const primarySignals = normalize([data.title, ...data.tags].join(" "));
  const description = normalize(data.description);

  return WORK_SIGNAL_GROUPS.reduce((score, { signals, weight }) => {
    const normalizedSignals = signals.map(normalize);

    if (normalizedSignals.some(signal => primarySignals.includes(signal))) {
      return score + weight;
    }
    if (normalizedSignals.some(signal => description.includes(signal))) {
      return score + 1;
    }
    return score;
  }, 0);
};

export const getWorkRelevantPosts = (
  posts: BlogPost[],
  limit = 3
): BlogPost[] =>
  posts
    .map((post, recencyIndex) => ({
      post,
      recencyIndex,
      score: getWorkRelevanceScore(post),
    }))
    .filter(({ score }) => score >= 5)
    .sort((a, b) => b.score - a.score || a.recencyIndex - b.recencyIndex)
    .slice(0, limit)
    .map(({ post }) => post);
