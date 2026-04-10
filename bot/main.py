import os
import random
import datetime
import urllib.request
import xml.etree.ElementTree as ET
import re
from google import genai
import collector

# 환경 변수 및 설정
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
BLOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../web/src/data/blog'))

# 카테고리 정의 (심플한 카테고리로 슬림화)
CATEGORIES = {
    "IT/AI/Security": "긱뉴스 및 해커뉴스 기반 최신 기술 동향",
    "Coffee": "스페셜티 커피 및 라이프스타일 트렌드",
    "Wine": "글로벌 와인 시장 및 테이스팅 인사이트",
    "Whiskey": "위스키 증류소 및 마켓 트렌드"
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
    """최근 작성된 포스트를 분석하여 겹치지 않는 카테고리를 선정하고 고퀄리티 RSS 데이터를 수집합니다."""
    all_categories = list(CATEGORIES.keys())
    eligible_categories = all_categories.copy()
    
    if recent_titles:
        recent_context = " ".join(recent_titles)
        for cat in all_categories:
            # 카테고리 이름이 최근 제목에 포함되어 있다면 제외 후보
            if cat.split("/")[0] in recent_context:
                if cat in eligible_categories and len(eligible_categories) > 1:
                    eligible_categories.remove(cat)
                    print(f"🚫 최근 주제와 겹칠 가능성이 있어 '{cat}' 제외")

    selected_category = random.choice(eligible_categories)
    print(f"🎯 선정된 카테고리: {selected_category}")
    
    # collector를 통해 단일 뉴스를 가져옴 (문자열 형태의 컨텍스트)
    news_context = collector.get_single_news_context(selected_category)
    
    return selected_category, news_context

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
        return None, None, None, None, None, None

    client = genai.Client()
    model_candidates = get_best_model_list(client)
    
    history_context = "\n".join([f"- {t}" for t in recent_titles]) if recent_titles else "없음"
    
    prompt = f"""
<instructions>
당신은 "{category}" 분야의 **데이터 입각한 통찰을 제공하는 전문 에디터**입니다. 
제공된 뉴스를 바탕으로 정보가 명확히 정돈된 블로그 포스트를 작성하십시오.
반드시 다음 단계를 거쳐 출력을 생성하십시오:

1. **사고 과정 (<thinking>)**: 최종 결과물을 내기 전, 뉴스의 핵심 가치를 파악하고, 전체적인 본문 구조를 어떻게 정돈할지, 그리고 지나치게 거창하지 않은 심플한 제목을 어떻게 지을지 논리적으로 추론하십시오.
2. **최종 출력**: 사고 과정을 바탕으로 제목, 요약, 태그, 카테고리, 이미지프롬프트, 그리고 구조화된 본문을 작성하십시오.
</instructions>

<style_guidelines>
- **제목**: 주제를 관통하면서도 군더더기 없는 **심플한 제목**을 작성하십시오. 거창한 수식어나 추상적인 비유(예: '~의 역설', '시대를 흔드는 ~')는 반드시 배제하십시오. 독자가 무엇에 관한 글인지 1초 만에 파악할 수 있도록 핵심 키워드 위주로 구성하십시오.
- **분량 및 상세도**: 반드시 **1,500자 이상의 풍부한 분량**으로 작성하십시오. 단순 요약이 아닌, 해당 주제의 배경, 원리, 파급력, 그리고 상세한 하우투(How-to)를 논리적으로 전개하여 '깊이 있는' 정보를 제공하십시오.
- **주제 집중도**: 제공된 **단 하나의 뉴스 주제**에만 온전히 집중하십시오. 다른 주제를 섞지 말고 해당 테마를 다각도에서 심층 분석하십시오.
- **본문 구조**: 정보 전달의 효율성을 위해 다음 구조를 따르십시오.
    1. **핵심 요약 (Key Takeaways)**: 본문 시작 부분에 가장 중요한 정보를 2~3개의 불렛 포인트로 정리하십시오.
    2. **상세 분석 및 가이드**: 분야별 특화 지침(GitHub 키워드, 테이스팅 노트 등)을 포함하여 일목요연하고 깊이 있게 설명하십시오. 인과관계와 구체적인 예시를 풍부하게 활용하십시오.
    3. **실천 제언 (Actionable Recommendations)**: 독자가 실제 도움을 얻거나 행동할 수 있는 구체적인 팁으로 마무리하십시오.
- **문체**: 미사여구를 줄이고 문장을 간결하게 다듬어 전체적으로 '정돈된' 느낌을 주십시오.
</style_guidelines>

<category_specific_instructions>
분야가 "{category}"임을 고려하여 다음 내용을 본문에 자연스럽게 포함하십시오:

[IT/AI/Security 분야일 경우]
- 새로운 소프트웨어나 도구 언급 시, 직접 링크 대신 **GitHub 검색용 키워드 및 공식 명칭**을 명확히 안내하십시오.
- 해당 기술의 **핵심 기능, 설치/사용법, 기대 효과, 실무 활용 방안(Use Cases)**을 섹션으로 나누어 설명하십시오.

[Hobby(Coffee, Wine, Whiskey) 분야일 경우]
- 전문가 수준의 **테이스팅 노트(향, 맛, 바디감 등)**와 **전문가 팁(보관, 페어링, 최적의 음용법)**을 상세히 기술하십시오.
- 역사적 배경이나 제조 공정의 특징 등 **깊이 있는 교양 정보**를 곁들여 전문성을 높이십시오.
</category_specific_instructions>

<context>
[최근 포스팅 내역 (중복 방지)]
{history_context}
</context>

<input>
[분석할 최신 뉴스 소스 및 요약]
{news_list}
</input>

[출력 포맷 가이드]
<thinking>
이 섹션에서 논리적 추론 과정을 먼저 전개하십시오.
선정된 단일 주제를 어떻게 1,500자 이상의 깊이 있는 글로 확장할지, 그리고 제목을 어떻게 심플하게 만들지 전략을 세우십시오.
</thinking>

제목: [제목]
카테고리: {category}
요약: [한 줄 요약]
태그: [태그1, 태그2, 태그3]
이미지프롬프트: [상세 영문 프롬프트]

---본문 시작---
[정해진 구조(핵심 요약 - 상세 분석 - 실천 제언)에 따라 정돈된 본문 작성]
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
                "제목": "제목 파싱 실패 (로직 확인 필요)",
                "요약": "요약 파싱 실패",
                "태그": "Trend,Insight",
                "카테고리": category,
                "이미지프롬프트": "Abstract digital technology background, 4k"
            }
            
            header_end_idx = 0
            for i, line in enumerate(lines[:15]):
                line = line.strip()
                if not line: continue
                
                for key in metadata.keys():
                    # 정규표현식 보강: 불렛포인트(-, *), 헤더(#), 강조(**) 등을 모두 무시하고 키 검색
                    pattern = re.compile(rf"^[#\s\-*]*\*?\*?{key}\*?\*?[:：]\s*(.*)", re.IGNORECASE)
                    match = pattern.match(line)
                    if match:
                        val = match.group(1).strip().replace("[", "").replace("]", "")
                        if val:
                            metadata[key] = val
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
    print(f"   [분야: {category} | 태그: {', '.join(final_tags)}]")

if __name__ == "__main__":
    try:
        print("--- 지능형 실시간 트렌드 미디어 봇 가동 (RSS 에디션) ---")
        
        # 최근 포스팅 이력 조회 (가장 최신 5개)
        recent_titles = get_recent_posts_info(5)
        
        # 주제 선정 및 뉴스 확보
        category, news_context = get_daily_topic_v2(recent_titles)
        
        if news_context and "수집된 뉴스가 없습니다" not in news_context:
            print(f"📊 {category} 분야 전문 데이터 확보 완료")
            print(f"   [선정된 주제 컨텍스트 요약: {news_context[:50]}...]")
            
            title, summary, tags, gen_category, image_prompt, content = generate_blog_post_v2(category, news_context, recent_titles)
            
            if title and content:
                print(f"📄 콘텐츠 생성 완료: '{title}' (분량: {len(content)}자)")
                save_post(title, summary, tags, gen_category or category, image_prompt, content)
                print("--- 포스팅 파이프라인 무사히 종료 ---")
            else:
                print("--- 콘텐츠 생성 실패 (API 또는 파싱 오류) ---")
        else:
            print("--- 뉴스 수집 실패 또는 데이터 부족으로 종료 ---")
            
    except Exception as e:
        print(f"🔥 치명적 오류 발생: {e}")
        import traceback
        traceback.print_exc()
