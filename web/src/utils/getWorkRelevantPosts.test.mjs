import assert from "node:assert/strict";
import test from "node:test";

import {
  getWorkRelevantPosts,
  getWorkRotationPenalty,
} from "./getWorkRelevantPosts.ts";

const REFERENCE_DATE = new Date("2026-08-18T07:00:00+09:00");
const DAY_IN_MS = 24 * 60 * 60 * 1000;

const makePost = ({ id, title, tags = [], description = "", daysOld = 0 }) => ({
  id,
  data: {
    title,
    tags,
    description,
    pubDatetime: new Date(REFERENCE_DATE.getTime() - daysOld * DAY_IN_MS),
  },
});

test("제목과 태그에 업무 신호가 없는 글은 설명에 관련 단어가 많아도 제외한다", () => {
  const unrelatedPost = makePost({
    id: "unrelated",
    title: "새로운 AI 모델 발표",
    tags: ["AI", "트렌드"],
    description: "업무 자동화, 생산성, 협업, 조직, 보고서 활용을 다룬다.",
  });
  const workPost = makePost({
    id: "work",
    title: "AI 업무 자동화 적용 가이드",
  });

  assert.deepEqual(
    getWorkRelevantPosts([unrelatedPost, workPost], 3, REFERENCE_DATE).map(
      post => post.id
    ),
    ["work"]
  );
});

test("발행 후 3일까지는 감점하지 않고 4일째부터 하루에 1점씩 감점한다", () => {
  assert.equal(
    getWorkRotationPenalty(
      makePost({ id: "day-3", title: "업무 활용", daysOld: 3 }),
      REFERENCE_DATE
    ),
    0
  );
  assert.equal(
    getWorkRotationPenalty(
      makePost({ id: "day-4", title: "업무 활용", daysOld: 4 }),
      REFERENCE_DATE
    ),
    1
  );
  assert.equal(
    getWorkRotationPenalty(
      makePost({ id: "old", title: "업무 활용", daysOld: 30 }),
      REFERENCE_DATE
    ),
    6
  );
});

test("오래된 추천보다 충분히 관련 있는 새 업무 글을 우선한다", () => {
  const stalePost = makePost({
    id: "stale",
    title: "업무 자동화 사례",
    daysOld: 10,
  });
  const freshPost = makePost({
    id: "fresh",
    title: "실무 적용 체크리스트",
    daysOld: 1,
  });

  assert.equal(
    getWorkRelevantPosts([stalePost, freshPost], 1, REFERENCE_DATE)[0].id,
    "fresh"
  );
});

test("대체 후보가 없으면 감점된 기존 업무 글도 유지한다", () => {
  const staleWorkPost = makePost({
    id: "stale-work",
    title: "업무 생산성 개선법",
    daysOld: 20,
  });
  const unrelatedPost = makePost({
    id: "unrelated",
    title: "AI 이미지 모델 소식",
    daysOld: 0,
  });

  assert.deepEqual(
    getWorkRelevantPosts([unrelatedPost, staleWorkPost], 3, REFERENCE_DATE).map(
      post => post.id
    ),
    ["stale-work"]
  );
});
