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

def generate_blog_post_v2(category, news_list):
    """수집된 여러 뉴스 정보를 종합하여 독창적인 제목과 본문을 작성합니다."""
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY 환경 변수가 없습니다. 작업 중단.")
        return None, None

    client = genai.Client()
    
    # 실시간 가용 모델 리스트 확보
    model_candidates = get_best_model_list(client)
    
    news_context = "\n".join([f"- {n}" for n in news_list])
    
    prompt = f"""
    당신은 "{category}" 분야의 전문 콘텐츠 에디터이자 전략적 블로거입니다. 
    제시된 여러 최신 뉴스 정보를 바탕으로 독자들에게 강력한 통찰을 제공하는 '오리지널' 블로그 포스트를 작성하세요.

    [참고할 최신 뉴스 소스들]
    {news_context}

    [필수 작성 및 구성 가이드라인]
    1. 독창적인 제목 (Catchy & Original Title):
       - **뉴스 헤드라인을 절대 그대로 사용하지 마십시오.** (표절 방지)
       - 위 뉴스들을 관통하는 하나의 주제를 담은 매력적인 제목을 새로 지으십시오.
       - 제목은 반드시 결과물의 첫 줄에 '제목: [내용]' 형식으로 작성하십시오.

    2. 다중 소스 종합 분석 (Synthesis):
       - 한 가지 뉴스만 요약하지 말고, 제공된 여러 뉴스 간의 연관성이나 흐름을 분석하여 하나의 완성된 글로 버무리십시오.

    3. PAS(Problem-Agitate-Solve) 방법론 적용:
       - **Problem**: 트렌드 속의 고민이나 궁금증 제기.
       - **Agitate**: 이 이슈의 중요성과 몰랐을 때의 위험성 분석.
       - **Solve**: 뉴스 기반의 해결책 및 독창적 인사이트 제공.

    4. SEO 및 가독성:
       - 본문 내 H1 금지. H2(##), H3(###)만 사용.
       - 문단은 3-4줄 단위로 짧게.
       - 핵심 요약은 반드시 **불릿 포인트** 사용.

    결과물 형식 예시:
    제목: [당신이 지은 독창적 제목]
    
    [본문 내용...]
    """
    
    for model_id in model_candidates:
        try:
            print(f"🚀 인공지능 모델 호출 시도 중: {model_id}...")
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
            )
            raw_text = response.text
            
            # 제목과 본문 분리 파싱
            lines = raw_text.strip().split('\n')
            title = "새로운 트렌드 분석"
            content_start_idx = 0
            
            if lines[0].startswith("제목:"):
                title = lines[0].replace("제목:", "").strip()
                content_start_idx = 1
            elif ":" in lines[0] and len(lines[0]) < 100:
                title = lines[0].split(":", 1)[1].strip()
                content_start_idx = 1
                
            body_text = "\n".join(lines[content_start_idx:]).strip()
            
            print(f"✨ 모델 {model_id}으로 독창적 콘텐츠 생성 대성공!")
            return title, body_text
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
    return None, None

def save_post(title, content):
    now = datetime.datetime.now()
    slug = f"auto-post-{now.strftime('%Y%m%d%H%M%S')}"
    
    frontmatter = f"""---
title: "{title}"
author: "AI Bot"
pubDatetime: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}
featured: false
draft: false
tags:
  - Trend
  - Automation
description: "{title}에 관한 실시간 트렌드 분석 포스트입니다."
---

"""
    filename = os.path.join(BLOG_DIR, f"{slug}.md")
    os.makedirs(BLOG_DIR, exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(frontmatter + content)
        
    print(f"새 포스트 저장 완료: {filename}")

if __name__ == "__main__":
    print("--- 실시간 트렌드 기반 자동화 블로그 봇 가동 ---")
    category, news_list = get_daily_topic_v2()
    print(f"분야: {category}")
    
    if news_list:
        print(f"수집된 뉴스 수: {len(news_list)}")
        title, content = generate_blog_post_v2(category, news_list)
        if title and content:
            save_post(title, content)
            print("--- 포스팅 파이프라인 무사히 종료 ---")
        else:
            print("--- 콘텐츠 생성 실패로 종료 ---")
    else:
        print("--- 뉴스 수집 실패로 종료 ---")
