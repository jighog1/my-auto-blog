import html
import ipaddress
import logging
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
SOURCE_FETCH_TIMEOUT = (5, 12)
MAX_SOURCE_BYTES = 600_000
URL_PATTERN = re.compile(r"https?://[^\s<>\"'\]\)]+", re.IGNORECASE)

# 검색 결과에 자주 섞이는 사용자 게시물·재배포 페이지는 근거 자료에서 제외합니다.
# 뉴스 집계·백과·동영상은 보조 출처로는 쓸 수 있지만 1차 출처로 세지 않습니다.
LOW_VALUE_SOURCE_DOMAINS = {
    "bsky.app",
    "blog.naver.com",
    "clien.net",
    "damoang.net",
    "jjoob.com",
    "modernorange.io",
    "promppy.com",
    "tistory.com",
    "vk.ru",
    "x.com",
    "zeli.app",
}
SUPPORTING_SOURCE_DOMAINS = {
    "news.hada.io",
    "news.ycombinator.com",
    "wikipedia.org",
    "youtube.com",
    "youtu.be",
}
SECONDARY_NEWS_DOMAINS = {
    "economictimes.indiatimes.com",
    "forbes.com",
    "futurism.com",
    "gadgets360.com",
    "marktechpost.com",
    "stork.ai",
    "techcrunch.com",
    "techgenyz.com",
    "the-decoder.com",
    "tradingkey.com",
}

# 편집 우선순위: AI 업무 적용을 가장 먼저, 개발자·IT 실무를 그다음으로 다룹니다.
AI_TOPIC_KEYWORDS = (
    "ai",
    "인공지능",
    "생성형",
    "llm",
    "language model",
    "machine learning",
    "머신러닝",
    "deep learning",
    "딥러닝",
    "openai",
    "anthropic",
    "chatgpt",
    "claude",
    "gemini",
    "copilot",
    "ai agent",
    "agentic",
    "에이전트",
    "rag",
    "mcp",
    "inference",
    "추론",
    "prompt",
    "프롬프트",
)
WORKPLACE_KEYWORDS = (
    "업무",
    "직장",
    "기업",
    "조직",
    "실무",
    "workplace",
    "workflow",
    "productivity",
    "enterprise",
    "business",
    "automation",
    "자동화",
    "협업",
    "문서",
    "데이터 분석",
)
DEVELOPER_TOPIC_KEYWORDS = (
    "developer",
    "development",
    "engineering",
    "programming",
    "software",
    "code",
    "coding",
    "개발",
    "프로그래밍",
    "소프트웨어",
    "api",
    "database",
    "데이터베이스",
    "cloud",
    "클라우드",
    "security",
    "보안",
    "devops",
    "github",
    "open source",
    "오픈소스",
)
LIFESTYLE_TOPIC_KEYWORDS = (
    "coffee",
    "커피",
    "wine",
    "와인",
    "whiskey",
    "whisky",
    "위스키",
    "rum",
    "럼주",
    "recipe",
    "레시피",
    "restaurant",
    "맛집",
    "travel",
    "여행",
    "fashion",
    "패션",
    "beauty",
    "뷰티",
    "golf",
    "골프",
)


def clean_html(raw_html):
    """HTML 태그와 엔티티를 제거합니다."""
    clean_text = re.sub(r"<.*?>", "", raw_html or "")
    return html.unescape(clean_text).strip()


def fetch_source_excerpt(value, max_chars=1800):
    """검색 스니펫 대신 실제 원문 응답에서 생성용 발췌를 가져옵니다."""
    url = normalize_source_url(value)
    if not url or is_low_value_source(url):
        return None

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "my-auto-blog/1.0 (+https://fivejh.com)"},
            timeout=SOURCE_FETCH_TIMEOUT,
            stream=True,
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if content_type and not (
            content_type.startswith("text/")
            or "json" in content_type
            or "xml" in content_type
        ):
            return None

        chunks = []
        received = 0
        for chunk in response.iter_content(chunk_size=16_384):
            if not chunk:
                continue
            remaining = MAX_SOURCE_BYTES - received
            if remaining <= 0:
                break
            chunks.append(chunk[:remaining])
            received += len(chunk[:remaining])

        encoding = response.encoding or "utf-8"
        raw_text = b"".join(chunks).decode(encoding, errors="replace")
        raw_text = re.sub(
            r"(?is)<(?:script|style|svg|noscript)\b.*?</(?:script|style|svg|noscript)>",
            " ",
            raw_text,
        )
        excerpt = clean_html(raw_text)
        # 원문 본문에 포함된 제3자 URL이 검증된 출처 목록으로 승격되지 않게 합니다.
        excerpt = URL_PATTERN.sub(" ", excerpt)
        excerpt = re.sub(r"\s+", " ", excerpt).strip()
        return excerpt[:max_chars] if len(excerpt) >= 120 else None
    except (requests.RequestException, UnicodeError) as error:
        logging.warning("원문 확인 실패 (%s): %s", url, error)
        return None


def normalize_source_url(value):
    """HTTP(S) 원문 URL만 정규화하고 그 외 값은 버립니다."""
    if not isinstance(value, str):
        return None

    candidate = html.unescape(value).strip().rstrip(".,;:!?")
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return None

    hostname = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or not hostname
        or parsed.username
        or parsed.password
    ):
        return None

    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        # `https://t`처럼 우연히 URL 정규식에 잡힌 값은 원문으로 인정하지 않습니다.
        if "." not in hostname:
            return None
    else:
        if not address.is_global:
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


def _domain_matches(hostname, domains):
    return any(
        hostname == domain or hostname.endswith(f".{domain}") for domain in domains
    )


def source_hostname(value):
    """정규화된 URL의 호스트 이름을 반환합니다."""
    normalized = normalize_source_url(value)
    return urlsplit(normalized).hostname if normalized else None


def is_low_value_source(value):
    """검색 결과 기반 재배포·커뮤니티 URL인지 확인합니다."""
    hostname = source_hostname(value)
    return bool(hostname and _domain_matches(hostname, LOW_VALUE_SOURCE_DOMAINS))


def is_probably_primary_source(value):
    """집계·일반 뉴스가 아닌 제품·프로젝트·연구의 직접 출처인지 판별합니다."""
    hostname = source_hostname(value)
    if not hostname:
        return False
    non_primary_domains = (
        LOW_VALUE_SOURCE_DOMAINS
        | SUPPORTING_SOURCE_DOMAINS
        | SECONDARY_NEWS_DOMAINS
    )
    return not _domain_matches(hostname, non_primary_domains)


def filter_source_urls(*values):
    """유효한 URL 중 저가치 검색 결과를 제거하고 순서를 보존합니다."""
    return [url for url in extract_source_urls(*values) if not is_low_value_source(url)]


def validate_source_mix(source_urls):
    """서로 다른 도메인 2곳과 직접 출처 1곳이 있는지 검사합니다."""
    normalized_urls = filter_source_urls(*source_urls)
    hostnames = {source_hostname(url) for url in normalized_urls}
    hostnames.discard(None)

    errors = []
    if len(normalized_urls) < 2:
        errors.append("사용 가능한 출처가 2개 미만입니다.")
    if len(hostnames) < 2:
        errors.append("출처 도메인이 2곳 미만입니다.")
    if not any(is_probably_primary_source(url) for url in normalized_urls):
        errors.append("제품·프로젝트·연구의 직접 출처가 없습니다.")
    return errors


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


def _contains_keyword(text, keyword):
    """영문 단어는 경계를 지키고 한국어 구문은 부분 일치로 찾습니다."""
    if keyword.isascii():
        return bool(
            re.search(
                rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])",
                text,
            )
        )
    return keyword in text


def topic_priority_score(item):
    """AI 업무 적용(1순위), 개발자·IT 실무(2순위) 기준 점수를 반환합니다."""
    text = " ".join(
        [
            clean_html(item.get("title", "")),
            clean_html(item.get("summary", "")),
        ]
    ).lower()

    if any(_contains_keyword(text, keyword) for keyword in LIFESTYLE_TOPIC_KEYWORDS):
        return -1

    ai_hits = sum(_contains_keyword(text, keyword) for keyword in AI_TOPIC_KEYWORDS)
    workplace_hits = sum(
        _contains_keyword(text, keyword) for keyword in WORKPLACE_KEYWORDS
    )
    developer_hits = sum(
        _contains_keyword(text, keyword) for keyword in DEVELOPER_TOPIC_KEYWORDS
    )

    if ai_hits:
        return 1000 + min(ai_hits, 4) * 50 + min(workplace_hits, 4) * 25 + min(
            developer_hits, 4
        ) * 10
    if developer_hits:
        return 500 + min(developer_hits, 4) * 20 + min(workplace_hits, 4) * 10
    return 0


def rank_news_items(news_items, excluded_urls=None):
    """최근 사용 출처와 비실무 주제를 제외하고 편집 우선순위대로 정렬합니다."""
    excluded = set(extract_source_urls(*(excluded_urls or [])))
    ranked = []

    for source_order, item in enumerate(news_items):
        link = normalize_source_url(item.get("link", ""))
        score = topic_priority_score(item)
        if not link or link in excluded or is_low_value_source(link) or score <= 0:
            continue

        if is_probably_primary_source(link):
            score += 40
        ranked.append((score, source_order, item))

    ranked.sort(key=lambda candidate: (-candidate[0], candidate[1]))
    return [item for _, _, item in ranked]


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
    feed_groups = []
    failures = []

    for feed_url in feeds:
        try:
            logging.info("뉴스 수집 중: %s -> %s", category, feed_url)
            feed = _fetch_feed(feed_url)

            feed_items = []
            for entry in feed.entries[:limit]:
                link = normalize_source_url(getattr(entry, "link", ""))
                title = clean_html(getattr(entry, "title", ""))
                if not link or not title:
                    logging.warning("제목 또는 원문 URL이 없는 RSS 항목을 제외합니다: %s", feed_url)
                    continue

                feed_items.append(
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
            if feed_items:
                feed_groups.append(feed_items)
        except (requests.RequestException, ValueError) as error:
            message = f"{feed_url}: {error}"
            failures.append(message)
            logging.error("RSS 수집 실패 (%s)", message)

    if not feed_groups and failures:
        raise RuntimeError("모든 RSS 피드 수집에 실패했습니다: " + " | ".join(failures))

    # 특정 피드 하나가 후보 전체를 독점하지 않도록 최신 항목을 교차 배치합니다.
    news_items = []
    for item_index in range(max((len(group) for group in feed_groups), default=0)):
        for group in feed_groups:
            if item_index < len(group):
                news_items.append(group[item_index])
    return news_items[:limit]


def get_formatted_news_context(category, limit=3):
    """콘텐츠 생성 프롬프트에 전달할 뉴스 목록을 텍스트로 포맷팅합니다."""
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


def deep_research(query, max_results=5):
    """DuckDuckGo 검색 결과 중 원문 URL이 확인되는 결과만 반환합니다."""
    if DDGS is None:
        logging.warning("ddgs 모듈이 없어 추가 검색을 건너뜁니다.")
        return "추가 검색 데이터를 가져오지 못했습니다. (라이브러리 미설치)"

    try:
        research_data = []
        seen_urls = set()
        for result in DDGS().text(query, max_results=max_results * 2):
            url = normalize_source_url(result.get("href"))
            if not url or url in seen_urls or is_low_value_source(url):
                continue
            seen_urls.add(url)
            excerpt = fetch_source_excerpt(url)
            if not excerpt:
                continue
            title = clean_html(result.get("title", "제목 없음"))
            research_data.append(f"- [{title}] {excerpt} (원문: {url})")
            if len(research_data) >= max_results:
                break

        if not research_data:
            return "추가 검색 데이터에서 유효한 원문 URL을 찾지 못했습니다."
        return "\n".join(research_data)
    except Exception as error:
        logging.error("Deep Research 중 오류 발생: %s", error)
        return "추가 검색 데이터를 가져오지 못했습니다."


def get_single_news_context(category, excluded_urls=None, candidate_limit=20):
    """우선순위가 가장 높은 미발행 RSS 주제와 검색 문맥을 구성합니다."""
    news_list = fetch_rss_news(category, limit=candidate_limit)
    ranked_news = rank_news_items(news_list, excluded_urls)
    if not ranked_news:
        return "수집된 뉴스가 없습니다."

    for item in ranked_news[:5]:
        main_excerpt = fetch_source_excerpt(item["link"])
        if is_probably_primary_source(item["link"]) and not main_excerpt:
            logging.warning("직접 출처를 읽을 수 없어 건너뜁니다: %s", item["link"])
            continue
        research_context = deep_research(item["title"])
        context = "\n".join(
            [
                "[[메인 주제 (RSS 기반)]]",
                f"제목: {item['title']} (출처: {item['source']})",
                f"원문 발췌: {main_excerpt or item['summary']}",
                f"원본 링크: {item['link']}",
                "",
                "[[추가 근거 자료]]",
                research_context,
            ]
        )
        source_errors = validate_source_mix(extract_source_urls(context))
        if source_errors:
            logging.warning(
                "출처 품질 기준 미달로 주제를 건너뜁니다: %s (%s)",
                item["title"],
                " ".join(source_errors),
            )
            continue

        logging.info(
            "선정된 주제: %s (우선순위 %s점)",
            item["title"],
            topic_priority_score(item),
        )
        return context

    raise RuntimeError(
        "직접 출처와 독립된 보조 출처를 모두 확보한 주제를 찾지 못했습니다."
    )


if __name__ == "__main__":
    for category_name in RSS_FEEDS:
        print(f"=== {category_name} 뉴스 테스트 ===")
        print(get_formatted_news_context(category_name, 2))
