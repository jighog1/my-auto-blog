import main

news_context = """
제목: React 19 출시 및 새로운 Compiler 소개 (출처: GeekNews)
요약: React 19가 드디어 정식 출시되었습니다. 가장 큰 특징은 React Compiler가 도입되어 useMemo, useCallback 등을 수동으로 작성할 필요가 없어졌다는 것입니다. 또한 Actions, useOptimistic 등의 새로운 훅이 추가되어 상태 관리가 더욱 쉬워졌습니다.
원본 링크: https://react.dev/blog/2024/04/25/react-19
"""

title, summary, tags, gen_category, image_prompt, content = main.generate_blog_post_v2("IT/AI/Security", news_context, [])

print("================= RESULT =================")
print(f"TITLE: {title}")
print(f"CONTENT: \n{content[:500]} ... [truncated]")
print("==========================================")
