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
    ],
    "Coffee": [
        "https://sprudge.com/feed" # Sprudge
    ],
    "Wine": [
        "https://www.decanter.com/feed/" # Decanter
    ],
    "Whiskey": [
        "https://thewhiskeywash.com/feed" # The Whiskey Wash
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

    # 다양한 소스를 섞어줍니다.
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

def get_single_news_context(category):
    """
    단일 주제에 집중하기 위해 가장 신선한 뉴스 1개만 추출하여 포맷팅합니다.
    """
    news_list = fetch_rss_news(category, limit=1)
    if not news_list:
        return "수집된 뉴스가 없습니다."
    
    item = news_list[0]
    context = f"제목: {item['title']} (출처: {item['source']})\n"
    context += f"요약: {item['summary']}...\n"
    context += f"원본 링크: {item['link']}\n"
    
    return context

if __name__ == "__main__":
    # 테스트 실행
    for cat in RSS_FEEDS.keys():
        print(f"=== {cat} 뉴스 테스트 ===")
        print("--- 하위 목록 모드 ---")
        print(get_formatted_news_context(cat, 2))
        print("--- 단일 주제 모드 ---")
        print(get_single_news_context(cat))
