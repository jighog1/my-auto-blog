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
    "IT/AI/Security": "긱뉴스 및 깃허브 상위 랭크 기반 최신 기술 동향"
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

def get_daily_topic_v2(recent_posts=None):
    """
    IT/AI/Security 카테고리로 고정하여 뉴스 주제를 선정합니다.
    """
    selected_category = "IT/AI/Security"
    print(f"🎯 주제 선정: 단일 카테고리 '{selected_category}' 고정 (취미 제외)")

    # 데이터 수집
    news_context = collector.get_single_news_context(selected_category)
    
    return selected_category, news_context

def get_recent_posts_info(count=6):
    """최근 작성된 포스트들의 정보를 가져와 비율 계산 및 중복 회피에 활용합니다."""
    post_info = []
    try:
        if not os.path.exists(BLOG_DIR):
            return []
            
        files = [f for f in os.listdir(BLOG_DIR) if f.endswith('.md')]
        files.sort(reverse=True)
        
        for filename in files[:count]:
            with open(os.path.join(BLOG_DIR, filename), 'r', encoding='utf-8') as f:
                content = f.read()
                title_match = re.search(r'title:\s*"(.*?)"', content)
                # 첫 번째 태그를 카테고리로 간주
                category_match = re.search(r'tags:\n\s+-\s+"(.*?)"', content)
                
                info = {
                    "title": title_match.group(1) if title_match else "Unknown",
                    "category": category_match.group(1) if category_match else "Unknown"
                }
                post_info.append(info)
        
        if post_info:
            print(f"📂 최근 포스팅 이력 확인됨 ({len(post_info)}건)")
        return post_info
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
당신은 10년 차 이상의 실무 경험을 가진 "{category}" 분야의 **시니어 엔지니어 겸 전문 에디터(Tech Insights Desk)**입니다. 
당신의 목표는 뉴스나 트렌드를 단순히 요약하는 것이 아니라, 독자가 실무에 즉시 써먹을 수 있는 **'에버그린(Evergreen) 튜토리얼 및 하우투(How-to)'** 형식의 고품질 칼럼을 작성하는 것입니다.

1. **사고 과정 (<thinking>)**: 주어진 뉴스를 기반으로 어떤 기술적 문제를 해결할 수 있을지, 어떤 아키텍처 다이어그램이 적합할지, 그리고 어떻게 2,500자 이상의 밀도 있는 실무 가이드를 구성할지 치열하게 고민하십시오.
2. **최종 출력**: 사고 과정을 거친 후, 마크다운(H2, H3, 리스트, 코드블럭)을 활용하여 구글 애드센스가 가장 선호하는 형태의 '가치 있는 정보'를 출력하십시오.
</instructions>

<style_guidelines>
- **제목**: "어떻게 ~하는가", "실무 적용 가이드", "~ 완벽 대비" 등 독자의 클릭을 유도하는 실무 지향적이고 심플한 제목을 작성하십시오.
- **분량 및 상세도**: 반드시 **2,500자 이상의 방대한 분량(최소 1,500단어)**으로 작성하십시오. 분량이 부족하면 실패한 글로 간주됩니다.
- **글의 성격 (Evergreen & How-to)**: 뉴스 전달보다는 해당 기술의 "도입 방법", "해결할 수 있는 문제", "타 기술과의 비교 분석"에 초점을 맞추어 수명이 긴 글을 쓰십시오.
- **페르소나 주입 (1인칭 경험담)**: 글의 서두(도입부)에 **반드시 1인칭 시점('필자는...', '내가 현업에서...')의 가상의 실무 경험담(Anecdote)**을 1~2문단 추가하여 글의 진정성과 권위(E-E-A-T)를 높이십시오.
- **본문 구조 (Markdown 최적화)**:
    1. **시니어 개발자의 실전 경험담 (Anecdote)**: 1인칭 시점으로 기술에 대한 첫인상이나 과거의 문제 해결 경험 서술.
    2. **핵심 원리 및 아키텍처 (with Mermaid)**: 해당 기술의 작동 원리를 **Mermaid.js 코드 블럭(```mermaid ... ```)**을 사용하여 시각적 다이어그램으로 반드시 하나 이상 표현하십시오.
    3. **상세 튜토리얼 및 실무 가이드 (Deep Dive)**: 구체적인 코드 스니펫(Python, JS 등), 설치 명령어, 또는 GitHub 검색 키워드를 포함한 실질적인 사용법.
    4. **장단점 및 대안 비교 (Pros & Cons)**: 객관적인 시각에서 한계점과 대안 도구 비교.
    5. **자주 묻는 질문 (FAQ)**: 실무자들이 흔히 겪는 2~3가지 문제와 해결책.
    6. **총평 (Conclusion)**: 향후 산업 변화 예측 및 마무리 인사.
</style_guidelines>

<category_specific_instructions>
분야가 "{category}"임을 고려하여 다음 내용을 포함하십시오:
- 긱뉴스(GeekNews) 트렌드를 기반으로 하되, 실무 개발 환경이나 시스템 아키텍처 관점에서 재해석하십시오.
- 추상적인 설명은 철저히 배제하고, 복붙해서 당장 돌려볼 수 있는 형태의 코드 스니펫이나 명확한 로직 플로우를 제공하십시오.
</category_specific_instructions>

<context>
[최근 포스팅 내역 (중복 방지)]
{history_context}
</context>

<input>
[분석할 최신 소스 및 요약]
{news_list}
</input>

[출력 포맷 가이드]
<thinking>
이 주제를 어떻게 '가이드/튜토리얼' 형태로 바꿀 것인지, 1인칭 경험담은 무엇으로 할지, Mermaid 다이어그램 구조는 어떻게 짤지 계획하십시오.
</thinking>

제목: [제목]
카테고리: {category}
요약: [한 줄 요약]
태그: [태그1, 태그2, 태그3]
이미지프롬프트: [상세 영문 프롬프트]

---본문 시작---
[정해진 구조(경험담 - Mermaid 아키텍처 - 실무 가이드 및 코드 - 비교 - FAQ - 총평)에 따라 완벽하게 마크다운으로 구조화된 2,500자 이상의 본문]
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
        
    frontmatter += f"""description: "{summary}"
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

def send_search_engine_ping():
    """포스팅 완료 후 구글과 빙에 사이트맵 핑을 보내 색인을 촉진합니다."""
    sitemap_url = "https://fivejh.com/sitemap-index.xml"
    ping_urls = [
        f"https://www.google.com/ping?sitemap={sitemap_url}",
        f"https://www.bing.com/ping?sitemap={sitemap_url}"
    ]
    
    print("🌍 검색엔진에 새 글 발행 알림(Ping)을 전송합니다...")
    for url in ping_urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req, timeout=10)
            if response.getcode() == 200:
                print(f"✅ Ping 성공: {url.split('//')[1].split('/')[0]}")
            else:
                print(f"⚠️ Ping 실패 ({response.getcode()}): {url}")
        except Exception as e:
            print(f"❌ Ping 전송 중 오류 발생 ({url.split('//')[1].split('/')[0]}): {e}")

if __name__ == "__main__":
    try:
        print("--- 지능형 실시간 트렌드 미디어 봇 가동 (RSS 에디션) ---")
        
        # 최근 포스팅 이력 조회 (상태 파악을 위해 6개 조회)
        recent_posts = get_recent_posts_info(6)
        recent_titles = [p['title'] for p in recent_posts]
        
        # 주제 선정 및 뉴스 확보
        category, news_context = get_daily_topic_v2(recent_posts)
        
        if news_context and "수집된 뉴스가 없습니다" not in news_context:
            print(f"📊 {category} 분야 전문 데이터 확보 완료")
            print(f"   [선정된 주제 컨텍스트 요약: {news_context[:50]}...]")
            
            title, summary, tags, gen_category, image_prompt, content = generate_blog_post_v2(category, news_context, recent_titles)
            
            if title and content:
                print(f"📄 콘텐츠 생성 완료: '{title}' (분량: {len(content)}자)")
                save_post(title, summary, tags, gen_category or category, image_prompt, content)
                
                # 검색엔진에 핑 전송
                send_search_engine_ping()
                
                print("--- 포스팅 파이프라인 무사히 종료 ---")
            else:
                print("--- 콘텐츠 생성 실패 (API 또는 파싱 오류) ---")
        else:
            print("--- 뉴스 수집 실패 또는 데이터 부족으로 종료 ---")
            
    except Exception as e:
        print(f"🔥 치명적 오류 발생: {e}")
        import traceback
        traceback.print_exc()
