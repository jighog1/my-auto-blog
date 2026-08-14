import html
import logging
import random
import re
from urllib.parse import urlsplit, urlunsplit

import feedparser
import requests

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

RSS_FEEDS = {
    "IT/AI/Security": [
        "https://news.hada.io/rss",
        "https://hnrss.org/frontpage",
    ]
}

RSS_TIMEOUT = (5, 20)
URL_PATTERN = re.compile(r"https?://[^\s<>\"'\]\)]+", re.IGNORECASE)


def clean_html(raw_html):
    """HTML 태그와 엔티티를 제거합니다."""
    clean_text = re.sub(r"<.*?>", "", raw_html or "")
    return html.unescape(clean_text).strip()


def normalize_source_url(value):
    """HTTP(S) 원문 URL만 정규화하고 그 외 값은 버립니다."""
    if not isinstance(value, str):
        return None

    candidate = html.unescape(value).strip().rstrip(".,;:!?")
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return None

    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None

    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "",
            parsed.query or "",
            "",
        )
    )


def extract_source_urls(*values):
    """문자열에서 HTTP(S) URL을 추출해 입력 순서대로 중복 제거합니다."""
    unique_urls = []
    seen = set()

    for value in values:
        if value is None:
            continue
        text = value if isinstance(value, str) else str(value)
        for match in URL_PATTERN.findall(text):
            normalized = normalize_source_url(match)
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_urls.append(normalized)

    return unique_urls


def _fetch_feed(feed_url):
    response = requests.get(
        feed_url,
        headers={"User-Agent": "my-auto-blog/1.0 (+https://fivejh.com)"},
        timeout=RSS_TIMEOUT,
    )
    response.raise_for_status()

    parsed_feed = feedparser.parse(response.content)
    if getattr(parsed_feed, "bozo", False):
        error = getattr(parsed_feed, "bozo_exception", "알 수 없는 파싱 오류")
        raise ValueError(f"RSS 파싱 실패: {error}")
    return parsed_feed


def fetch_rss_news(category, limit=5):
    """RSS 피드에서 원문 URL이 확인되는 최신 뉴스를 가져옵니다."""
    feeds = RSS_FEEDS.get(category, [])
    news_items = []
    failures = []

    for feed_url in feeds:
        try:
            logging.info("뉴스 수집 중: %s -> %s", category, feed_url)
            feed = _fetch_feed(feed_url)

            for entry in feed.entries[:limit]:
                link = normalize_source_url(getattr(entry, "link", ""))
                title = clean_html(getattr(entry, "title", ""))
                if not link or not title:
                    logging.warning("제목 또는 원문 URL이 없는 RSS 항목을 제외합니다: %s", feed_url)
                    continue

                news_items.append(
                    {
                        "title": title,
                        "link": link,
                        "summary": clean_html(
                            getattr(entry, "summary", title)
                        )[:500],
                        "source": clean_html(
                            feed.feed.get("title", "Unknown Source")
                        ),
                    }
                )
        except (requests.RequestException, ValueError) as error:
            message = f"{feed_url}: {error}"
            failures.append(message)
            logging.error("RSS 수집 실패 (%s)", message)

    if not news_items and failures:
        raise RuntimeError("모든 RSS 피드 수집에 실패했습니다: " + " | ".join(failures))

    if category != "IT/AI/Security":
        random.shuffle(news_items)
    return news_items[:limit]


def get_formatted_news_context(category, limit=3):
    """Gemini 프롬프트에 전달할 뉴스 목록을 텍스트로 포맷팅합니다."""
    news_list = fetch_rss_news(category, limit)
    if not news_list:
        return "수집된 뉴스가 없습니다."

    lines = []
    for index, item in enumerate(news_list, 1):
        lines.extend(
            [
                f"{index}. {item['title']} (출처: {item['source']})",
                f"   - 요약: {item['summary']}",
                f"   - 링크: {item['link']}",
                "",
            ]
        )
    return "\n".join(lines)


def deep_research(query, max_results=3):
    """DuckDuckGo 검색 결과 중 원문 URL이 확인되는 결과만 반환합니다."""
    if DDGS is None:
        logging.warning("ddgs 모듈이 없어 추가 검색을 건너뜁니다.")
        return "추가 검색 데이터를 가져오지 못했습니다. (라이브러리 미설치)"

    try:
        research_data = []
        seen_urls = set()
        for result in DDGS().text(query, max_results=max_results):
            url = normalize_source_url(result.get("href"))
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            title = clean_html(result.get("title", "제목 없음"))
            body = clean_html(result.get("body", ""))[:500]
            research_data.append(f"- [{title}] {body} (원문: {url})")

        if not research_data:
            return "추가 검색 데이터에서 유효한 원문 URL을 찾지 못했습니다."
        return "\n".join(research_data)
    except Exception as error:
        logging.error("Deep Research 중 오류 발생: %s", error)
        return "추가 검색 데이터를 가져오지 못했습니다."


def get_single_news_context(category):
    """최신 RSS 주제 하나와 해당 주제의 검색 문맥을 구성합니다."""
    news_list = fetch_rss_news(category, limit=1)
    if not news_list:
        return "수집된 뉴스가 없습니다."

    item = news_list[0]
    logging.info("선정된 주제: %s - Deep Research를 시작합니다.", item["title"])
    research_context = deep_research(item["title"])

    return "\n".join(
        [
            "[[메인 주제 (RSS 기반)]]",
            f"제목: {item['title']} (출처: {item['source']})",
            f"요약: {item['summary']}",
            f"원본 링크: {item['link']}",
            "",
            "[[Deep Research 기반 추가 심층 데이터]]",
            research_context,
        ]
    )


if __name__ == "__main__":
    for category_name in RSS_FEEDS:
        print(f"=== {category_name} 뉴스 테스트 ===")
        print(get_formatted_news_context(category_name, 2))
