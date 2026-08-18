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
  { weight: 6, signals: ["개발 생산성"] },
  { weight: 4, signals: ["코딩", "보안"] },
] as const;

const DAY_IN_MS = 24 * 60 * 60 * 1000;
const WORK_RELEVANCE_THRESHOLD = 5;
const ROTATION_GRACE_DAYS = 3;
const MAX_ROTATION_PENALTY = 6;

const normalize = (value: string) => value.toLocaleLowerCase("ko-KR");

const scoreSignals = (text: string, descriptionOnly = false) =>
  WORK_SIGNAL_GROUPS.reduce((score, { signals, weight }) => {
    const normalizedSignals = signals.map(normalize);

    return normalizedSignals.some(signal => text.includes(signal))
      ? score + (descriptionOnly ? 1 : weight)
      : score;
  }, 0);

export const getPrimaryWorkRelevanceScore = ({ data }: BlogPost) =>
  scoreSignals(normalize([data.title, ...data.tags].join(" ")));

export const getWorkRelevanceScore = (post: BlogPost) =>
  getPrimaryWorkRelevanceScore(post) +
  scoreSignals(normalize(post.data.description), true);

export const getWorkRotationPenalty = (
  { data }: BlogPost,
  referenceDate: Date
) => {
  const ageInDays = Math.max(
    0,
    Math.floor(
      (referenceDate.getTime() - data.pubDatetime.getTime()) / DAY_IN_MS
    )
  );

  return Math.min(
    Math.max(ageInDays - ROTATION_GRACE_DAYS, 0),
    MAX_ROTATION_PENALTY
  );
};

export const getWorkRelevantPosts = (
  posts: BlogPost[],
  limit = 3,
  referenceDate = new Date()
): BlogPost[] =>
  posts
    .map((post, recencyIndex) => ({
      post,
      recencyIndex,
      score: getWorkRelevanceScore(post),
      primaryScore: getPrimaryWorkRelevanceScore(post),
      rotationPenalty: getWorkRotationPenalty(post, referenceDate),
    }))
    .filter(({ primaryScore }) => primaryScore >= WORK_RELEVANCE_THRESHOLD)
    .sort(
      (a, b) =>
        b.score - b.rotationPenalty - (a.score - a.rotationPenalty) ||
        a.recencyIndex - b.recencyIndex
    )
    .slice(0, limit)
    .map(({ post }) => post);
