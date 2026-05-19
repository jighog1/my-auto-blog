import feedparser
import random
import logging
import re

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

RSS_FEEDS = {
    "IT/AI/Security": [
        "https://news.hada.io/rss",  # GeekNews (Korean)
        "https://hnrss.org/frontpage"  # Hacker News (English)
    ]
}

def clean_html(raw_html):
    """HTML 태그 제거"""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext

def fetch_rss_news(category, limit=5):
    """
    지정된 카테고리의 RSS 피드에서 최신 뉴스를 가져옵니다.
    """
    feeds = RSS_FEEDS.get(category, [])
    news_items = []

    for feed_url in feeds:
        try:
            logging.info(f"뉴스 수집 중: {category} -> {feed_url}")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:limit]:
                # 제목과 링크, 가능한 경우 요약 정보 추출
                news_items.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": clean_html(getattr(entry, 'summary', entry.title))[:200],
                    "source": feed.feed.get('title', 'Unknown Source')
                })
        except Exception as e:
            logging.error(f"RSS 수집 중 오류 발생 ({feed_url}): {e}")

    # IT 카테고리의 경우 소스 순서(긱뉴스 우선)를 유지하기 위해 셔플링을 생략합니다.
    if category != "IT/AI/Security":
        random.shuffle(news_items)
    
    return news_items[:limit]

def get_formatted_news_context(category, limit=3):
    """
    Gemini 프롬프트에 삽입할 수 있도록 뉴스 목록을 텍스트로 포맷팅합니다.
    """
    news_list = fetch_rss_news(category, limit)
    if not news_list:
        return "수집된 뉴스가 없습니다."

    context = ""
    for idx, item in enumerate(news_list, 1):
        context += f"{idx}. {item['title']} (출처: {item['source']})\n"
        context += f"   - 요약: {item['summary']}...\n"
        context += f"   - 링크: {item['link']}\n\n"
    
    return context

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None
    logging.warning("duckduckgo_search 모듈이 설치되지 않았습니다. 추가 검색 기능이 제한됩니다.")

def deep_research(query, max_results=3):
    """DuckDuckGo 검색을 통해 주제에 대한 심층 데이터를 수집합니다."""
    if not DDGS:
        return "추가 검색 데이터를 가져오지 못했습니다. (라이브러리 미설치)"
    
    try:
        results = DDGS().text(query, max_results=max_results)
        research_data = []
        for r in results:
            research_data.append(f"- [{r.get('title')}] {r.get('body')} (출처: {r.get('href')})")
        return "\n".join(research_data)
    except Exception as e:
        logging.error(f"Deep Research 중 오류 발생: {e}")
        return "추가 검색 데이터를 가져오지 못했습니다."

def get_single_news_context(category):
    """
    단일 주제에 집중하기 위해 가장 신선한 뉴스 1개만 추출하고, 
    해당 주제로 Deep Research를 수행하여 문맥을 획기적으로 확장합니다.
    """
    news_list = fetch_rss_news(category, limit=1)
    if not news_list:
        return "수집된 뉴스가 없습니다."
    
    item = news_list[0]
    
    logging.info(f"선정된 주제: {item['title']} - Deep Research를 시작합니다...")
    research_context = deep_research(item['title'])
    
    context = f"[[메인 주제 (RSS 기반)]]\n"
    context += f"제목: {item['title']} (출처: {item['source']})\n"
    context += f"요약: {item['summary']}...\n"
    context += f"원본 링크: {item['link']}\n\n"
    
    context += f"[[Deep Research 기반 추가 심층 데이터]]\n"
    context += f"{research_context}\n"
    
    return context

if __name__ == "__main__":
    # 테스트 실행
    for cat in RSS_FEEDS.keys():
        print(f"=== {cat} 뉴스 테스트 ===")
        print("--- 하위 목록 모드 ---")
        print(get_formatted_news_context(cat, 2))
        print("--- 단일 주제 모드 ---")
        print(get_single_news_context(cat))
