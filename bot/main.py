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

# 카테고리 정의 및 고도화된 검색 쿼리
CATEGORIES = {
    "IT/기술 트렌드": "최신 IT 트렌드 차세대 소프트웨어 기술 동향",
    "정보보안 이슈": "사이버 보안 위협 해킹 사고 분석 보안 기술 트렌드",
    "AI 및 자동화": "인공지능 산업 적용 사례 생성형 AI 기술 혁신 도구",
    "글로벌 경제/비즈니스": "세계 경제 지표 금리 변동 시장 분석 경영 인사이트",
    "사회/정치 이슈": "국내외 주요 정치 사회 이슈 정책 변화 시사 분석",
    "과학/우주 탐사": "최신 과학 기술 발견 우주 탐사 프로젝트 양자 컴퓨팅",
    "환경/신재생 에너지": "탄소 중립 신재생 에너지 기술 기후 위기 대응책",
    "인문학/철학/심리": "인문학적 통찰 현대 철학 심리학 트렌드 행동 경제학",
    "문화/예술/라이프": "글로벌 문화 트렌드 예술 시장 라이프스타일 혁신",
    "상식/교양": "역사적 사건 배경 지식 세계사 상식 교양 인사이트"
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
    """수집된 뉴스 정보를 바탕으로 전문가급 인사이트가 담긴 제목, 요약, 태그, 본문을 작성합니다."""
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY 환경 변수가 없습니다. 작업 중단.")
        return None, None, None, None, None

    client = genai.Client()
    model_candidates = get_best_model_list(client)
    
    news_context = "\n".join([f"- {n}" for n in news_list])
    history_context = "\n".join([f"- {t}" for t in recent_titles]) if recent_titles else "없음"
    
    prompt = f"""
<instructions>
당신은 "{category}" 분야의 **수석 전략 컨설턴트 및 전문 기술 미디어 편집자**입니다. 
제공된 뉴스를 바탕으로 독창적인 통찰이 담긴 블로그 포스트를 작성하십시오.
반드시 다음 단계를 거쳐 출력을 생성하십시오:

1. **사고 과정 (<thinking>)**: 최종 결과물을 내기 전, 뉴스 데이터의 핵심 가치, 최근 포스팅과의 차별점, 그리고 독자에게 줄 수 있는 전략적 조언을 논리적으로 추론하십시오.
2. **최종 출력**: 사고 과정을 바탕으로 제목, 요약, 태그, 카테고리, 이미지프롬프트, 그리고 PAS 구조의 본문을 작성하십시오.
</instructions>

<context>
[최근 포스팅 내역 (중복 방지)]
{history_context}
</context>

<input>
[분석할 최신 뉴스 소스]
{news_context}
</input>

<examples>
제목: AI 에이전트의 시대: 단순 자동화를 넘어 자율적 비즈니스 파트너로
카테고리: AI 및 자동화
요약: 생성형 AI가 단순 도구를 넘어 의사결정과 실행을 독립적으로 수행하는 에이전트로 진화하고 있습니다.
태그: AI,Agent,Automation,Future,Business
이미지프롬프트: A cinematic 3D render of a futuristic robot hand shaking a human hand, glowing circuit patterns, soft professional lighting, 4k.
---본문 시작---
[PAS 구조의 고품질 콘텐츠...]
</examples>

[출력 포맷 가이드]
<thinking>
이 섹션에서 논리적 추론 과정을 먼저 전개하십시오.
</thinking>

제목: [제목]
카테고리: {category}
요약: [한 줄 요약]
태그: [태그1, 태그2, 태그3]
이미지프롬프트: [상세 영문 프롬프트]

---본문 시작---
[H2, H3 헤더를 사용한 본문 내용 작성]
    """
    
    for model_id in model_candidates:
        try:
            print(f"🚀 글로벌 규칙 규격화 프롬프트 호출 중: {model_id}...")
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
            )
            raw_text = response.text
            
            # 파싱 로직 (Thinking 태그 제외하고 본데이터만 추출)
            # <thinking>...</thinking> 부분을 제거
            clean_text = re.sub(r'<thinking>.*?</thinking>', '', raw_text, flags=re.DOTALL).strip()
            lines = clean_text.split('\n')
            
            metadata = {
                "제목": "새로운 트렌드 분석",
                "요약": "최신 시장 동향과 기술적 통찰을 분석합니다.",
                "태그": "Trend,Insight",
                "카테고리": category,
                "이미지프롬프트": "Abstract digital technology background, 4k"
            }
            
            header_end_idx = 0
            for i, line in enumerate(lines[:15]):
                for key in metadata.keys():
                    if line.startswith(f"{key}:"):
                        metadata[key] = line.replace(f"{key}:", "").strip().replace("[", "").replace("]", "")
                        header_end_idx = i + 1
            
            body_lines = lines[header_end_idx:]
            if body_lines and "---본문 시작---" in body_lines[0]:
                body_lines = body_lines[1:]
            
            body_text = "\n".join(body_lines).strip()
            
            print(f"✨ 글로벌 규칙 기반 콘텐츠 생성 완료!")
            return metadata["제목"], metadata["요약"], metadata["태그"], metadata["카테고리"], metadata["이미지프롬프트"], body_text
            
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                continue
            print(f"❌ {model_id} 오류: {e}")
            continue
                
    return None, None, None, None, None, None

import urllib.parse

def save_post(title, summary, tags_str, category, image_prompt, content):
    now = datetime.datetime.now()
    slug = f"auto-post-{now.strftime('%Y%m%d%H%M%S')}"
    
    # 태그 처리 및 정제 (YAML 예약어 및 빈 문자열 방어)
    raw_tags = [t.strip().replace('"', '').replace("'", "") for t in tags_str.split(',') if t.strip()]
    cleaned_tags = []
    for tag in raw_tags:
        # 너무 짧거나 특수기호만 있는 경우 제외
        if len(tag) > 1 and not tag.startswith('-'):
            cleaned_tags.append(tag)
            
    if category not in cleaned_tags:
        cleaned_tags.insert(0, category)
    
    # 중복 제거 및 최종 리스트 (최대 6개)
    final_tags = list(dict.fromkeys(cleaned_tags))[:6]
    
    # 이미지 프롬프트 URL 인코딩
    encoded_prompt = urllib.parse.quote(image_prompt) if image_prompt else "technology,futuristic,3d_render"
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=630&nologo=true"

    # 프론트매터 구성
    frontmatter = f"""---
title: "{title}"
author: "AI Bot"
pubDatetime: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}
featured: false
draft: false
tags:
"""
    for tag in final_tags:
        # 안전을 위해 모든 태그를 이중 따옴표로 감쌈
        frontmatter += f'  - "{tag}"\n'
        
    frontmatter += f"""ogImage: "{image_url}"
description: "{summary}"
---

"""

    # 본문 상단에 시각적 요약 카드 삽입
    summary_card = f"""> [!IMPORTANT]
> **분야**: {category}  
> **한 줄 요약**: {summary}

---

"""
    
    filename = os.path.join(BLOG_DIR, f"{slug}.md")
    os.makedirs(BLOG_DIR, exist_ok=True)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(frontmatter + summary_card + content)
        
    print(f"✅ 새 포스트 저장 완료: {filename}")
    print(f"   [분야: {category} | 태그: {', '.join(tags)}]")

if __name__ == "__main__":
    print("--- 지능형 실시간 트렌드 미디어 봇 가동 ---")
    
    # 최근 포스팅 이력 조회 (가장 최신 5개)
    recent_titles = get_recent_posts_info(5)
    
    category, news_list = get_daily_topic_v2(recent_titles)
    
    if news_list:
        print(f"📊 {category} 분야 뉴스 {len(news_list)}건 확보")
        title, summary, tags, gen_category, image_prompt, content = generate_blog_post_v2(category, news_list, recent_titles)
        
        if title and content:
            save_post(title, summary, tags, gen_category or category, image_prompt, content)
            print("--- 포스팅 파이프라인 무사히 종료 ---")
        else:
            print("--- 콘텐츠 생성 실패로 종료 ---")
    else:
        print("--- 뉴스 수집 실패로 종료 ---")
