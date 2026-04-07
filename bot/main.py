import os
import random
import datetime
from google import genai
import requests

# 환경 변수 및 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BLOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../web/src/content/blog'))

# 1. 주제 선정 모의 함수
def get_daily_topic():
    # 실제 환경에서는 Google Trends API 등을 활용할 수 수 있습니다.
    topics = [
        "2026년 프론트엔드 웹 개발 트렌드",
        "자동화 시스템과 생산성 향상 노하우",
        "개발자를 위한 멘탈 관리법",
        "생성형 AI 시대, 개발자의 생존 전략",
        "초보자도 따라 할 수 있는 SEO 최적화 가이드"
    ]
    return random.choice(topics)

# 2. 본문 생성 함수 (Gemini)
def generate_blog_post(topic):
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY 환경 변수가 없습니다. 더미 텍스트를 반환합니다.")
        return f"## {topic} 관련 임시 내용입니다.\n\n이것은 API KEY 없이 생성된 더미 콘텐츠입니다. API 키가 주어지면 이 영역에 AI가 작성한 긴 글이 들어갑니다."

    client = genai.Client()
    prompt = f"""
    당신은 전문적인 IT/테크 블로거입니다. 다음 주제에 대해 블로그 포스트를 작성해 주세요:
    주제: {topic}
    
    요구사항:
    - 한국어로 작성할 것.
    - SEO에 최적화되도록 구성. (H2, H3 태그 등 적절히 사용)
    - 도입부 - 본문 - 결론 구조로 작성.
    - 친근하고 읽기 쉬운 문체 사용.
    - 제목(Title) 메타데이터나 H1은 제외하고 본문(H2 이하)부터 반환할 것.
    """
    
    try:
        target_model = 'gemini-2.5-flash'  # 기본 Fallback
        try:
            # 1. API에 접속하여 현재 계정이 사용 가능한 모델 리스트 조회
            available_models = [m.name.replace('models/', '') for m in client.models.list()]
            
            # 2. 가장 안정적이고 속도가 빠른 '정식 릴리즈된 Flash 모델' 우선 순위 목록 (preview, exp 제외)
            whitelist = [
                'gemini-3.0-flash', 
                'gemini-2.5-flash', 
                'gemini-2.0-flash', 
                'gemini-1.5-flash'
            ]
            
            # 3. 화이트리스트 중 내 계정(available_models)에서 사용할 수 있는 가장 최신 버전을 선택
            for w_model in whitelist:
                if w_model in available_models:
                    target_model = w_model
                    break
        except Exception as e:
            print(f"모델 목록 조회 중 오류(무시가능): {e}")

        print(f"🚀 안정성 확인 후 최종 선택된 생성 AI 모델: {target_model}")

        # 선택된 모델로 글 작성 요청 수행
        response = client.models.generate_content(
            model=target_model,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"콘텐츠 생성 중 오류: {e}")
        return f"## 생성 오류 발생\n오류 내용: {e}"

# 3. 마크다운 파일 저장 (Astro 포맷에 맞춤)
def save_post(topic, content):
    now = datetime.datetime.now()
    date_str = now.strftime('%Y-%m-%d')
    slug = f"auto-post-{now.strftime('%Y%m%d%H%M%S')}"
    
    # Astro 블로그 Frontmatter 구조
    frontmatter = f"""---
title: "{topic}"
description: "{topic}에 관한 자동 생성된 포스트입니다."
pubDate: "{now.strftime('%b %d %Y')}"
heroImage: "/blog-placeholder-about.jpg"
---

"""
    filename = os.path.join(BLOG_DIR, f"{slug}.md")
    
    # 폴더가 없으면 생성 (최초 실행 대비)
    os.makedirs(BLOG_DIR, exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(frontmatter + content)
        
    print(f"새 포스트 작성 완료: {filename}")

if __name__ == "__main__":
    print("--- 자동화 블로그 포스터 시작 ---")
    topic = get_daily_topic()
    print(f"선정된 주제: {topic}")
    
    content = generate_blog_post(topic)
    save_post(topic, content)
    print("--- 포스팅 파이프라인 종료 ---")
