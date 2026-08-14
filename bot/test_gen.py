"""실제 Gemini API 호출을 수동으로 확인하는 개발용 스크립트입니다."""

import main


NEWS_CONTEXT = """
제목: React 19 출시 및 새로운 Compiler 소개 (출처: React)
요약: React 19와 Compiler 관련 공식 안내입니다.
원본 링크: https://react.dev/blog/2024/04/25/react-19
"""


if __name__ == "__main__":
    title, summary, tags, category, content = main.generate_blog_post_v2(
        "IT/AI/Security",
        NEWS_CONTEXT,
        [],
    )
    print("================= RESULT =================")
    print(f"TITLE: {title}")
    print(f"SUMMARY: {summary}")
    print(f"TAGS: {tags}")
    print(f"CATEGORY: {category}")
    print(f"CONTENT:\n{content[:500]} ... [truncated]")
    print("==========================================")
