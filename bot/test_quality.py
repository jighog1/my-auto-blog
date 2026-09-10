import json
import os
import unittest
from unittest import mock

import collector
import main


SOURCE_URLS = [
    "https://example.com/source",
    "https://docs.example.org/guide",
]


class FakeResponse:
    def __init__(self, output_text):
        self.output_text = output_text


class FakeResponsesApi:
    def __init__(self, output_text):
        self.output_text = output_text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse(self.output_text)


class FakeOpenAIClient:
    def __init__(self, output_text):
        self.responses = FakeResponsesApi(output_text)


class FakeSourceResponse:
    headers = {"Content-Type": "text/html; charset=utf-8"}
    encoding = "utf-8"

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        del chunk_size
        yield (
            b"<html><style>hidden</style><body>"
            + ("실제 원문 내용입니다. ".encode("utf-8") * 20)
            + b" https://third-party.example/link"
            + b"</body></html>"
        )


class QualityPolicyTests(unittest.TestCase):
    @staticmethod
    def structured_body():
        sections = "\n\n".join(
            f"## {heading}\n\n검증 가능한 설명입니다."
            for heading in main.REQUIRED_BODY_HEADINGS
        )
        citations = (
            "\n\n확인된 사실은 [제품 원문](https://example.com/source)과 "
            "[기술 문서](https://docs.example.org/guide)를 근거로 합니다."
        )
        artifact = (
            "\n\n| 판단 항목 | 확인 기준 |\n"
            "|---|---|\n"
            "| 적용 범위 | 담당자가 승인할 수 있는가 |"
        )
        return sections + citations + artifact + ("\n\n추가 설명입니다." * 400)

    def test_generation_uses_only_luna_with_structured_output(self):
        payload = json.dumps(
            {
                "title": "업무에 적용하는 AI 변화",
                "summary": "업무 영향을 설명하는 요약입니다.",
                "tags": ["AI", "업무자동화", "생산성"],
                "category": "IT/AI/Security",
                "body": self.structured_body(),
            },
            ensure_ascii=False,
        )
        client = FakeOpenAIClient(payload)
        context = "\n".join(
            ["뉴스 문맥", *SOURCE_URLS]
        )

        with (
            mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            mock.patch("main.OpenAI", return_value=client) as openai_client,
        ):
            title, _, _, category, content = main.generate_blog_post_v2(
                "IT/AI/Security", context, []
            )

        openai_client.assert_called_once_with(api_key="test-key")
        self.assertEqual(title, "업무에 적용하는 AI 변화")
        self.assertEqual(category, "IT/AI/Security")
        self.assertIn("## 참고자료", content)
        request = client.responses.calls[0]
        self.assertEqual(request["model"], "gpt-5.6-luna")
        self.assertEqual(request["reasoning"], {"effort": "medium"})
        self.assertEqual(request["text"]["format"]["type"], "json_schema")

    def test_missing_openai_key_fails_fast(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                main.generate_blog_post_v2(
                    "IT/AI/Security", "\n".join(SOURCE_URLS), []
                )

    def test_source_urls_are_normalized_and_invalid_hosts_are_removed(self):
        text = """
        HTTPS://Example.COM/article?id=1#section
        https://example.com/article?id=1
        http://docs.example.org/guide.
        https://t
        http://127.0.0.1/private
        ftp://example.com/file
        """
        self.assertEqual(
            collector.extract_source_urls(text),
            [
                "https://example.com/article?id=1",
                "http://docs.example.org/guide",
            ],
        )

    def test_low_value_sources_are_filtered(self):
        urls = collector.filter_source_urls(
            "https://sample.tistory.com/post",
            "https://example.com/original",
            "https://x.com/example/status/1",
        )
        self.assertEqual(urls, ["https://example.com/original"])

    @mock.patch("collector.requests.get", return_value=FakeSourceResponse())
    def test_source_excerpt_uses_actual_http_response(self, request_get):
        excerpt = collector.fetch_source_excerpt("https://example.com/original")
        self.assertIn("실제 원문 내용입니다.", excerpt)
        self.assertNotIn("hidden", excerpt)
        self.assertNotIn("third-party.example", excerpt)
        request_get.assert_called_once()

    def test_source_mix_requires_diversity_and_direct_source(self):
        errors = collector.validate_source_mix(
            [
                "https://news.hada.io/topic?id=1",
                "https://news.ycombinator.com/item?id=2",
            ]
        )
        self.assertIn("제품·프로젝트·연구의 직접 출처가 없습니다.", errors)
        self.assertEqual(
            collector.validate_source_mix(
                [
                    "https://news.hada.io/topic?id=1",
                    "https://example.com/original",
                ]
            ),
            [],
        )

    def test_topic_ranking_matches_editorial_priority(self):
        items = [
            {
                "title": "개발자를 위한 새 데이터베이스 도구",
                "summary": "오픈소스 소프트웨어 개발 도구",
                "link": "https://example.com/developer",
            },
            {
                "title": "AI로 기업 업무 자동화하기",
                "summary": "직장인 워크플로와 생산성 개선",
                "link": "https://example.com/ai-work",
            },
            {
                "title": "AI가 추천한 주말 커피 여행",
                "summary": "맛집과 여행 코스",
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
            items, ["https://example.com/already-used"]
        )
        self.assertEqual(
            [item["link"] for item in ranked],
            ["https://example.com/new-topic"],
        )

    def test_prompt_encodes_added_value_requirements(self):
        prompt = main._build_prompt(
            "IT/AI/Security",
            "뉴스 문맥 " + " ".join(SOURCE_URLS),
            [],
            SOURCE_URLS,
        )
        self.assertIn("친근하지만 객관적인 리포터", prompt)
        self.assertIn("1순위 독자는 AI 트렌드", prompt)
        self.assertIn("실제 의사결정이나 작업에 재사용", prompt)
        self.assertIn("서로 다른 출처를 본문에서 최소 2개 인용", prompt)
        self.assertIn("실행 체크리스트", prompt)

    def test_short_body_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "본문이 3500자 미만"):
            main.validate_post(
                "안전한 제목",
                "검증 가능한 한 줄 요약입니다.",
                ["IT", "AI", "Security"],
                "너무 짧은 본문",
                SOURCE_URLS,
            )

    def test_long_or_hyped_title_is_rejected(self):
        body = self.structured_body()
        with self.assertRaisesRegex(ValueError, "제목이 52자를 초과"):
            main.validate_post(
                "가" * (main.MAX_TITLE_LENGTH + 1),
                "업무 영향을 설명하는 요약입니다.",
                ["IT", "AI", "Security"],
                body,
                SOURCE_URLS,
            )
        with self.assertRaisesRegex(ValueError, "과장된 표현"):
            main.validate_post(
                "새 AI 모델 완벽 분석",
                "업무 영향을 설명하는 요약입니다.",
                ["IT", "AI", "Security"],
                body,
                SOURCE_URLS,
            )

    def test_required_briefing_sections_are_enforced(self):
        with self.assertRaisesRegex(ValueError, "필수 섹션이 없습니다"):
            main.validate_post(
                "업무에 적용하는 AI 변화",
                "업무 영향을 설명하는 요약입니다.",
                ["IT", "AI", "Security"],
                "가" * main.MIN_BODY_LENGTH,
                SOURCE_URLS,
            )

    def test_inline_sources_and_reusable_artifact_are_required(self):
        body_without_artifact = "\n\n".join(
            f"## {heading}\n\n검증 가능한 설명입니다."
            for heading in main.REQUIRED_BODY_HEADINGS
        )
        body_without_artifact += (
            "\n\nhttps://example.com/source\n\n"
            "https://docs.example.org/guide"
            + ("\n\n추가 설명입니다." * 400)
        )
        with self.assertRaisesRegex(ValueError, "재사용 가능한 실무 도구"):
            main.validate_post(
                "업무에 적용하는 AI 변화",
                "업무 영향을 설명하는 요약입니다.",
                ["IT", "AI", "Security"],
                body_without_artifact,
                SOURCE_URLS,
            )

        with self.assertRaisesRegex(ValueError, "본문 인용 출처"):
            main.validate_post(
                "업무에 적용하는 AI 변화",
                "업무 영향을 설명하는 요약입니다.",
                ["IT", "AI", "Security"],
                self.structured_body().replace(
                    "https://docs.example.org/guide", ""
                ),
                SOURCE_URLS,
            )

    def test_similar_recent_title_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "최근 글과 주제가 지나치게 유사"):
            main.validate_post(
                "업무에 적용하는 AI 자동화 변화",
                "업무 영향을 설명하는 요약입니다.",
                ["IT", "AI", "Security"],
                self.structured_body(),
                SOURCE_URLS,
                recent_titles=["AI 자동화 변화를 업무에 적용하기"],
            )

    def test_structured_briefing_passes_quality_policy(self):
        main.validate_post(
            "업무에 적용하는 AI 변화",
            "업무 영향을 설명하는 요약입니다.",
            ["IT", "AI", "Security"],
            self.structured_body(),
            SOURCE_URLS,
        )

    def test_reference_section_uses_only_deduplicated_sources(self):
        rendered = main.append_reference_section(
            "가" * main.MIN_BODY_LENGTH,
            [
                "https://example.com/source#fragment",
                "https://example.com/source",
                "https://docs.example.org/guide",
            ],
        )
        self.assertIn("## 참고자료", rendered)
        self.assertEqual(rendered.count("https://example.com/source"), 1)
        self.assertIn("https://docs.example.org/guide", rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
