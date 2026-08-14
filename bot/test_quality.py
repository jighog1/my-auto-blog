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

    def test_short_body_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "본문이 3500자 미만"):
            main.validate_post(
                "안전한 제목",
                "검증 가능한 한 줄 요약입니다.",
                ["IT", "AI", "Security"],
                "너무 짧은 본문",
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
