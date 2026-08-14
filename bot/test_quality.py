import os
import unittest
from unittest import mock

import collector
import main


class FakeModel:
    def __init__(self, name, supported_actions):
        self.name = name
        self.supported_actions = supported_actions


class FakeModelsApi:
    def __init__(self, models):
        self._models = models

    def list(self):
        return self._models


class FakeClient:
    def __init__(self, models):
        self.models = FakeModelsApi(models)


class QualityPolicyTests(unittest.TestCase):
    @staticmethod
    def structured_body():
        sections = "\n\n".join(
            f"## {heading}\n\n검증 가능한 설명입니다."
            for heading in main.REQUIRED_BODY_HEADINGS
        )
        return sections + ("\n\n추가 설명입니다." * 400)

    def test_model_filtering_prefers_compatible_configured_model(self):
        models = [
            FakeModel("models/gemini-3.6-flash", ["generateContent"]),
            FakeModel("models/gemini-2.5-flash", ["generateContent"]),
            FakeModel("models/gemini-2.5-flash-preview-tts", ["generateContent"]),
            FakeModel("models/gemini-embedding-2-preview", ["embedContent"]),
            FakeModel("models/gemini-omni-flash-preview", ["generateContent"]),
        ]
        with mock.patch.dict(os.environ, {"GEMINI_MODEL": "gemini-2.5-flash"}):
            candidates = main.get_best_model_list(FakeClient(models))

        self.assertEqual(candidates[0], "gemini-2.5-flash")
        self.assertEqual(
            set(candidates), {"gemini-3.6-flash", "gemini-2.5-flash"}
        )

        with mock.patch.dict(
            os.environ,
            {"GEMINI_MODEL": "gemini-omni-flash-preview"},
        ):
            fallback_candidates = main.get_best_model_list(FakeClient(models))
        self.assertEqual(fallback_candidates[0], "gemini-3.6-flash")
        self.assertNotIn("gemini-omni-flash-preview", fallback_candidates)

    def test_source_url_extraction_normalizes_and_deduplicates(self):
        text = """
        원문: HTTPS://Example.COM/article?id=1#section
        중복: https://example.com/article?id=1
        검색: http://docs.example.org/guide.
        제외: ftp://example.com/file
        """
        self.assertEqual(
            collector.extract_source_urls(text),
            [
                "https://example.com/article?id=1",
                "http://docs.example.org/guide",
            ],
        )

    def test_topic_ranking_prioritizes_ai_workplace_then_developer(self):
        items = [
            {
                "title": "새로운 Python 패키지 관리자 공개",
                "summary": "개발자 도구와 오픈소스 생태계 소식",
                "link": "https://example.com/developer",
            },
            {
                "title": "기업 문서 업무를 돕는 AI 에이전트",
                "summary": "워크플로 자동화와 생산성 향상 사례",
                "link": "https://example.com/ai-work",
            },
            {
                "title": "AI가 추천한 여름 커피 레시피",
                "summary": "집에서 즐기는 취미 생활",
                "link": "https://example.com/coffee",
            },
        ]

        ranked = collector.rank_news_items(items)

        self.assertEqual(
            [item["link"] for item in ranked],
            ["https://example.com/ai-work", "https://example.com/developer"],
        )

    def test_topic_ranking_excludes_recently_published_source(self):
        items = [
            {
                "title": "업무 자동화를 위한 생성형 AI",
                "summary": "기업 워크플로 적용 방법",
                "link": "https://example.com/already-used#section",
            },
            {
                "title": "개발자를 위한 보안 자동화",
                "summary": "실무 보안 워크플로",
                "link": "https://example.com/new-topic",
            },
        ]

        ranked = collector.rank_news_items(
            items,
            ["https://example.com/already-used"],
        )

        self.assertEqual([item["link"] for item in ranked], ["https://example.com/new-topic"])

    def test_prompt_encodes_audience_goals_and_reporter_tone(self):
        prompt = main._build_prompt(
            "IT/AI/Security",
            "뉴스 문맥 https://example.com/source",
            [],
            ["https://example.com/source"],
        )

        self.assertIn("친근하지만 객관적인 리포터", prompt)
        self.assertIn("1순위 독자는 AI 트렌드", prompt)
        self.assertIn("업무 적용 아이디어 확보", prompt)
        self.assertIn("3분 안에 핵심", prompt)

    def test_short_body_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "본문이 3500자 미만"):
            main.validate_post(
                "안전한 제목",
                "검증 가능한 한 줄 요약입니다.",
                ["IT", "AI", "Security"],
                "너무 짧은 본문",
                ["https://example.com/source"],
            )

    def test_long_or_hyped_title_is_rejected(self):
        body = self.structured_body()
        with self.assertRaisesRegex(ValueError, "제목이 52자를 초과"):
            main.validate_post(
                "가" * (main.MAX_TITLE_LENGTH + 1),
                "업무 영향을 설명하는 요약입니다.",
                ["IT", "AI", "Security"],
                body,
                ["https://example.com/source"],
            )

        with self.assertRaisesRegex(ValueError, "과장된 표현"):
            main.validate_post(
                "새 AI 모델 완벽 분석",
                "업무 영향을 설명하는 요약입니다.",
                ["IT", "AI", "Security"],
                body,
                ["https://example.com/source"],
            )

    def test_required_briefing_sections_are_enforced(self):
        with self.assertRaisesRegex(ValueError, "필수 섹션이 없습니다"):
            main.validate_post(
                "업무에 적용하는 AI 변화",
                "업무 영향을 설명하는 요약입니다.",
                ["IT", "AI", "Security"],
                "가" * main.MIN_BODY_LENGTH,
                ["https://example.com/source"],
            )

    def test_structured_briefing_passes_quality_policy(self):
        main.validate_post(
            "업무에 적용하는 AI 변화",
            "업무 영향을 설명하는 요약입니다.",
            ["IT", "AI", "Security"],
            self.structured_body(),
            ["https://example.com/source"],
        )

    def test_reference_section_uses_only_deduplicated_sources(self):
        content = "가" * main.MIN_BODY_LENGTH
        rendered = main.append_reference_section(
            content,
            [
                "https://example.com/source#fragment",
                "https://example.com/source",
                "https://docs.example.com/article",
            ],
        )

        self.assertIn("## 참고자료", rendered)
        self.assertEqual(rendered.count("https://example.com/source"), 1)
        self.assertIn("https://docs.example.com/article", rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
