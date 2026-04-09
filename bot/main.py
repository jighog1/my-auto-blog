import os
import random
import datetime
import urllib.request
import xml.etree.ElementTree as ET
import re
from google import genai

# 환경 변수 및 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BLOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../web/src/data/blog'))

# 카테고리 정의 및 검색 키워드 (시사, 경제, 과학, 인문 등 대폭 확장)
CATEGORIES = {
    "IT/기술 트렌드": "IT 트렌드 소프트웨어 신기술",
    "정보보안 이슈": "사이버 보안 해킹 이슈 데이터 유출",
    "AI 및 자동화": "인공지능 생성형 AI 대규모언어모델",
    "글로벌 경제/비즈니스": "세계 경제 금리 주식 경영 인사이트",
    "사회/정치 이슈": "국내외 주요 정치 사회 이슈 시사 트렌드",
    "과학/우주 탐사": "최신 과학 발견 우주 탐사 양자 역학",
    "환경/신재생 에너지": "기후 위기 신재생 에너지 친환경 기술",
    "인문학/철학/심리": "인문학 통찰 철학적 사고 심리학 트렌드",
    "문화/예술/라이프": "베스트셀러 전시회 라이프스타일 트렌드",
    "상식/교양": "알아두면 좋은 상식 역사적 사건 세계사"
}

def fetch_trend_news(category):
    """지정한 카테고리의 최신 뉴스 제목 3개를 가져옵니다."""
    query = CATEGORIES.get(category, "최신 트렌드")
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

def get_daily_topic_v2(recent_titles=None):
    """최근 작성된 포스트 제목들을 분석하여 겹치지 않는 카테고리를 우선 선정하고 뉴스를 수집합니다."""
    all_categories = list(CATEGORIES.keys())
    eligible_categories = all_categories.copy()
    
    # 최근 3~5개 포스트 제목에서 키워드를 추출하여 최근 사용된 카테고리를 추측
    if recent_titles:
        recent_context = " ".join(recent_titles)
        # 간단한 매칭으로 최근 카테고리 제외 시도
        for cat, keywords in CATEGORIES.items():
            # 카테고리 이름이나 키워드 중 일부가 최근 제목에 포함되어 있다면 제외 후보
            main_keywords = keywords.split()[:2] + [cat.split("/")[0]]
            for wk in main_keywords:
                if wk in recent_context:
                    if cat in eligible_categories and len(eligible_categories) > 3:
                        eligible_categories.remove(cat)
                        print(f"🚫 최근 주제와 겹칠 가능성이 있어 '{cat}' 제외")
                    break

    # 필터링된 카테고리 중 랜덤 선택, 필터링 후 남은게 너무 적으면 전체에서 선택
    selected_category = random.choice(eligible_categories)
    print(f"🎯 선정된 카테고리: {selected_category}")
    
    news_list = fetch_trend_news(selected_category)
    
    if not news_list:
        return selected_category, ["최신 " + selected_category + " 트렌드 분석"]
    
    return selected_category, news_list

def get_recent_posts_info(count=3):
    """최근 작성된 포스트들의 제목을 가져와 중복을 피하기 위한 정보로 활용합니다."""
    titles = []
    try:
        if not os.path.exists(BLOG_DIR):
            return []
            
        files = [f for f in os.listdir(BLOG_DIR) if f.endswith('.md')]
        # 파일명 기반 역순 정렬 (auto-post-YYYYMMDD...)
        files.sort(reverse=True)
        
        for filename in files[:count]:
            with open(os.path.join(BLOG_DIR, filename), 'r', encoding='utf-8') as f:
                content = f.read()
                # 간단한 정규식으로 title 추출
                match = re.search(r'title:\s*"(.*?)"', content)
                if match:
                    titles.append(match.group(1))
        
        if titles:
            print(f"📂 최근 포스팅 이력 확인됨: {titles}")
        return titles
    except Exception as e:
        print(f"⚠️ 최근 포스팅 이력 조회 중 오류: {e}")
        return []

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

def generate_blog_post_v2(category, news_list, recent_titles=None):
    """수집된 여러 뉴스 정보를 종합하여 독창적인 제목, 이미지 키워드, 본문을 작성합니다."""
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY 환경 변수가 없습니다. 작업 중단.")
        return None, None, None

    client = genai.Client()
    
    # 실시간 가용 모델 리스트 확보
    model_candidates = get_best_model_list(client)
    
    news_context = "\n".join([f"- {n}" for n in news_list])
    history_context = "\n".join([f"- {t}" for t in recent_titles]) if recent_titles else "없음"
    
    prompt = f"""
    당신은 "{category}" 분야의 전문 콘텐츠 에디터이자 전략적 블로거입니다. 
    제시된 여러 최신 뉴스 정보를 바탕으로 독자들에게 강력한 통찰을 제공하는 '오리지널' 블로그 포스트를 작성하세요.

    [최근 포스팅된 주제들 (중복 피하기)]
    {history_context}

    [참고할 최신 뉴스 소스들]
    {news_context}

    [필수 작성 및 구성 가이드라인]
    1. 중복 및 표절 방지:
       - **뉴스 헤드라인을 절대 제목으로 그대로 사용하지 마십시오.**
       - 최근 주제들과 겹치지 않는 새로운 시각을 제공하십시오.

    2. 이미지 및 멀티미디어:
       - **이미지 키워드**: 글의 분위기에 맞는 **영문 키워드 3~5개**를 선정하십시오. 
       - **주의**: 키워드는 반드시 콤마(,)로 구분하여 한 줄로 작성하십시오. (예: AI,illustration,futuristic,blue)
       - 실사 사진보다는 주제와 어울리는 **'Illustration', '3D render', 'Minimalist'** 스타일이 포함되도록 하십시오.
       - 결과 상단에 '이미지키워드: [키워드1,키워드2...]' 형식으로 명시하십시오.
       - **Mermaid 다이어그램**: 정보의 구조나 흐름을 시각화할 수 있는 경우, 반드시 `mermaid` 코드 블록을 포함하십시오.

    3. PAS(Problem-Agitate-Solve) 방법론 적용 및 본문 작성:
       - **Solve** 섹션에서 뉴스 기반의 해결책 및 독창적 인사이트를 제공하십시오.
       - 본문 내 H1 금지. H2(##), H3(###)만 사용.
       - 문단은 짧게 불릿 포인트를 적극 활용하십시오.

    결과물 형식 예시:
    제목: [당신이 지은 독창적 제목]
    이미지키워드: [영문키워드]
    
    [본문 내용(Mermaid 다이어그램 포함)...]
    """
    
    for model_id in model_candidates:
        try:
            print(f"🚀 인공지능 모델 호출 시도 중: {model_id}...")
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
            )
            raw_text = response.text
            
            # 파싱 및 데이터 추출
            lines = raw_text.strip().split('\n')
            title = "새로운 트렌드 분석"
            image_keyword = "technology"
            content_start_idx = 0
            
            # 제목 및 이미지 키워드 추출 로직
            header_count = 0
            for i, line in enumerate(lines[:5]):
                if line.startswith("제목:"):
                    title = line.replace("제목:", "").strip()
                    header_count = i + 1
                elif line.startswith("이미지키워드:"):
                    image_keyword = line.replace("이미지키워드:", "").strip().replace("[", "").replace("]", "")
                    header_count = i + 1
            
            body_text = "\n".join(lines[header_count:]).strip()
            
            print(f"✨ 모델 {model_id}으로 독창적 콘텐츠 및 시나리오 생성 완료!")
            return title, image_keyword, body_text
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
                
    print("🚨 모든 가용 모델이 실패했습니다.")
    return None, None, None

import urllib.parse

def save_post(title, image_keyword, content):
    now = datetime.datetime.now()
    slug = f"auto-post-{now.strftime('%Y%m%d%H%M%S')}"
    
    # 이미지 키워드 URL 인코딩 (공백 및 특수문자 처리)
    # quote_plus를 사용하여 공백을 +로 변환 (더 표준적인 URL 방식)
    encoded_keyword = urllib.parse.quote_plus(image_keyword) if image_keyword else "technology"
    
    # LoremFlickr 검색 리다이렉트 활용
    image_url = f"https://loremflickr.com/1200/630/{encoded_keyword}"

    frontmatter = f"""---
title: "{title}"
author: "AI Bot"
pubDatetime: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}
featured: false
draft: false
tags:
  - Trend
  - Automation
ogImage: "{image_url}"
description: "{title}에 관한 실시간 트렌드 분석 포스트입니다."
---

"""
    filename = os.path.join(BLOG_DIR, f"{slug}.md")
    os.makedirs(BLOG_DIR, exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(frontmatter + content)
        
    print(f"새 포스트 저장 완료: {filename} (이미지 키워드: {image_keyword})")

if __name__ == "__main__":
    print("--- 실시간 트렌드 기반 자동화 블로그 봇 가동 ---")
    
    # 최근 포스팅 이력 조회 (가장 최신 5개로 확장)
    recent_titles = get_recent_posts_info(5)
    
    category, news_list = get_daily_topic_v2(recent_titles)
    print(f"분야: {category}")
    
    if news_list:
        print(f"수집된 뉴스 수: {len(news_list)}")
        title, image_keyword, content = generate_blog_post_v2(category, news_list, recent_titles)
        if title and content:
            save_post(title, image_keyword, content)
            print("--- 포스팅 파이프라인 무사히 종료 ---")
        else:
            print("--- 콘텐츠 생성 실패로 종료 ---")
    else:
        print("--- 뉴스 수집 실패로 종료 ---")
