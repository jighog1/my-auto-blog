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

def get_best_model_list(client):
    """사용자님의 API 키로 접근 가능한 모델 중 가장 좋은 'Flash' 및 'Pro' 모델을 순서대로 찾아옵니다."""
    try:
        # API를 통해 현재 계정에서 사용 가능한 모델 목록 조회
        raw_models = [m.name for m in client.models.list()]
        
        # 1. Flash 모델들을 찾아 최신순(역순)으로 정렬 (예: 2.0-flash > 1.5-flash)
        flash_models = sorted([m for m in raw_models if "flash" in m.lower() and "experimental" not in m.lower()], reverse=True)
        # 2. Pro 모델들을 찾아 최신순으로 정렬
        pro_models = sorted([m for m in raw_models if "pro" in m.lower() and "experimental" not in m.lower()], reverse=True)
        
        # Flash -> Pro 순서로 후보군 형성
        final_list = flash_models + pro_models
        
        if not final_list:
            # 절대 망하지 않기 위한 기본 모델 강제 삽입
            final_list = ["gemini-2.0-flash", "gemini-1.5-flash"]
            
        print(f"🔍 실시간 탐색된 가용 모델 리스트: {final_list}")
        return final_list
    except Exception as e:
        print(f"⚠️ 모델 목록 조회 중 오류 발생 (기본값 사용): {e}")
        return ["gemini-2.0-flash", "gemini-1.5-flash"]

def generate_blog_post_v2(category, topic, news_list):
    """수집된 뉴스 정보를 바탕으로 제미나이가 글을 작성합니다."""
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY 환경 변수가 없습니다. 작업 중단.")
        return None

    client = genai.Client()
    
    # 실시간 가용 모델 리스트 확보
    model_candidates = get_best_model_list(client)
    
    news_context = "\n".join([f"- {n}" for n in news_list])
    
    prompt = f"""
    당신은 "{category}" 분야의 전문 콘텐츠 에디터이자 전략적 블로거입니다. 
    제시된 최신 뉴스 정보를 바탕으로 독자들에게 강력한 통찰을 제공하는 프리미엄 블로그 포스트를 작성하세요.

    [오늘의 참고 뉴스]
    {news_context}

    [작성할 포스트 주제]
    {topic}

    [필수 작성 가이드라인]
    1. PAS(Problem-Agitate-Solve) 방법론 적용:
       - **Problem (문제 제기)**: 독자가 직면한 현실적인 고민이나 최신 트렌드 속에서 가질 수 있는 궁금증을 제시하며 흥미를 유발하세요.
       - **Agitate (문제 심화)**: 이 이슈가 왜 지금 중요한지, 제대로 알지 못했을 때 어떤 기회비용이 발생하는지 뉴스 배경을 바탕으로 상세히 분석하세요.
       - **Solve (해결책 및 인사이트)**: 수집된 뉴스 정보들을 종합하여 독자가 얻어야 할 실질적인 정보와 미래 전망을 명확하게 제시하세요.

    2. 시맨틱 구조 및 SEO:
       - 제목(H1)은 시스템에서 별도로 처리하므로 **본문 내에 H1 태그를 절대 사용하지 마십시오.**
       - 본문의 소제목은 반드시 **H2(##)**와 **H3(###)**만을 사용하여 논리적 계층을 만드십시오.

    3. 가독성(Scannability) 최적화:
       - 모든 문단은 모바일 가독성을 고려하여 **최대 3~4줄 단위**로 짧게 끊어서 작성하십시오.
       - 글의 핵심 요약이나 인사이트는 반드시 **불릿 포인트(Bullet point)**를 사용하여 한눈에 들어오게 정리하십시오.

    4. 문체 및 구성:
       - 전문적이면서도 친근한 어조를 유지하십시오. (한국어 작성)
       - 단순 뉴스 요약이 아닌, 당신만의 독창적인 분석과 인사이트가 포함되어야 합니다.
       - 출처 이름(언론사 등)을 직접 언급하기보다 '최신 보고서에 따르면', '업계 전문가들은'과 같은 자연스러운 문구를 사용하십시오.
    """
    
    for model_id in model_candidates:
        try:
            print(f"🚀 인공지능 모델 호출 시도 중: {model_id}...")
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
            )
            print(f"✨ 모델 {model_id}으로 콘텐츠 생성 대성공!")
            return response.text
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                print(f"⚠️ {model_id} 모델 할당량 초과(429). 다음 모델로 넘어갑니다...")
                continue
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                print(f"⚠️ {model_id} 모델을 찾을 수 없음(404). 다음 모델을 시도합니다...")
                continue
            else:
                print(f"❌ {model_id} 처리 중 예상치 못한 오류 발생: {e}")
                continue
                
    print("🚨 모든 가용 모델이 실패했습니다. API 키 설정이나 할당량을 다시 확인해 주세요.")
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
