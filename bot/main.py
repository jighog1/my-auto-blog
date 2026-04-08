import os
import random
import datetime
import urllib.request
import xml.etree.ElementTree as ET
from google import genai

# 환경 변수 및 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BLOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../web/src/data/blog'))

# 카테고리 정의 및 검색 키워드
CATEGORIES = {
    "IT/기술 트렌드": "IT 트렌드 소프트웨어 기술",
    "정보보안 이슈": "사이버 보안 해킹 이슈",
    "AI 및 자동화": "인공지능 생성형 AI",
    "경제 및 비즈니스": "경제 트렌드 비즈니스 인사이트"
}

def fetch_trend_news(category):
    """지정한 카테고리의 최신 뉴스 제목 3개를 가져옵니다."""
    query = CATEGORIES.get(category, "최신 기술")
    encoded_query = urllib.parse.quote(query)
    # Google News RSS URL
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    
    try:
        with urllib.request.urlopen(url) as response:
            xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        news_items = []
        for item in root.findall('.//item')[:3]:
            title = item.find('title').text
            news_items.append(title)
        
        return news_items
    except Exception as e:
        print(f"뉴스 수집 중 오류 발생: {e}")
        return []

def get_daily_topic_v2():
    """랜덤하게 카테고리를 정하고 해당 분야의 뉴스를 수집하여 주제를 도출합니다."""
    category = random.choice(list(CATEGORIES.keys()))
    news_list = fetch_trend_news(category)
    
    if not news_list:
        return category, "최신 트렌드 분석", []
    
    # 첫 번째 뉴스 제목을 기반으로 주제를 생성하거나 뉴스 리스트 자체를 반환
    main_news = news_list[0].split(" - ")[0] # 언론사 이름 제거 시도
    return category, main_news, news_list

def generate_blog_post_v2(category, topic, news_list):
    """수집된 뉴스 정보를 바탕으로 제미나이가 글을 작성합니다."""
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY 환경 변수가 없습니다. 작업 중단.")
        return None

    client = genai.Client()
    
    news_context = "\n".join([f"- {n}" for n in news_list])
    
    prompt = f"""
    당신은 "{category}" 전문 블로거입니다. 
    오늘의 주요 뉴스 테마는 다음과 같습니다:
    {news_context}

    이 뉴스 정보들을 바탕으로 "{topic}"에 관한 깊이 있는 분석 포스트를 작성해 주세요.
    
    요구사항:
    - 한국어로 작성할 것.
    - SEO에 최적화되도록 구성. (H2, H3 태그 등 적절히 사용)
    - 단순 나열이 아닌, 뉴스 내용을 종합하여 독자들에게 도움이 되는 '인사이트'를 제공할 것.
    - 도입부 - 본문 - 결론 구조로 작성.
    - 제목(Title) 메타데이터나 H1은 제외하고 본문(H2 이하)부터 반환할 것.
    - 출처나 언론사 이름은 본문에 직접적으로 언급하지 말고 정보 위주로 작성할 것.
    """
    
    # 할당량 초과 대비 시도할 모델 후보군
    model_candidates = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro']
    
    for model_id in model_candidates:
        try:
            print(f"🚀 인공지능 모델 호출 중: {model_id}...")
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
            )
            print(f"✨ 모델 {model_id}으로 콘텐츠 생성 성공!")
            return response.text
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                print(f"⚠️ {model_id} 모델 할당량 초과(429). 다음 가용 모델로 전환을 시도합니다...")
                continue
            else:
                print(f"❌ {model_id} 호출 중 예상치 못한 오류 발생: {e}")
                continue
                
    print("🚨 모든 가용 모델이 실패했습니다.")
    return None

def save_post(topic, content):
    now = datetime.datetime.now()
    slug = f"auto-post-{now.strftime('%Y%m%d%H%M%S')}"
    
    frontmatter = f"""---
title: "{topic}"
author: "AI Bot"
pubDatetime: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}
featured: false
draft: false
tags:
  - Trend
  - Automation
description: "{topic}에 관한 실시간 트렌드 분석 포스트입니다."
---

"""
    filename = os.path.join(BLOG_DIR, f"{slug}.md")
    os.makedirs(BLOG_DIR, exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(frontmatter + content)
        
    print(f"새 포스트 저장 완료: {filename}")

if __name__ == "__main__":
    print("--- 실시간 트렌드 기반 자동화 블로그 봇 가동 ---")
    category, topic, news_list = get_daily_topic_v2()
    print(f"분야: {category}")
    print(f"헤드라인: {topic}")
    
    content = generate_blog_post_v2(category, topic, news_list)
    if content:
        save_post(topic, content)
        print("--- 포스팅 파이프라인 무사히 종료 ---")
    else:
        print("--- 콘텐츠 생성 실패로 종료 ---")
