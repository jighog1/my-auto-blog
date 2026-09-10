# AI 브리핑룸

**일하는 사람의 AI 브리핑.** 공식 자료와 신뢰할 수 있는 보조 자료를 바탕으로, 직장인이 AI 변화를 빠르게 이해하고 업무에 사용할 판단 기준과 도구를 얻도록 돕는 Astro 블로그입니다.

## 실행 흐름

1. GeekNews와 Hacker News RSS를 타임아웃 및 HTTP 상태 검사와 함께 수집합니다.
2. AI 업무 적용 주제를 먼저, 개발자·IT 실무 주제를 다음으로 평가합니다. 생활·취미 주제와 최근 사용한 원문은 제외합니다.
3. `ddgs` 검색 결과에서 커뮤니티·재배포 페이지를 제거하고 실제 원문 응답을 읽을 수 있는 자료만 남깁니다.
4. 서로 다른 도메인의 출처가 두 곳 이상이고, 제품·프로젝트·연구의 읽을 수 있는 직접 출처가 있는 주제만 선택합니다.
5. OpenAI Responses API와 `gpt-5.6-luna`로 초안을 만들고 출처·중복·구조·표현 품질을 검사합니다.
6. 검사를 통과한 글만 Markdown으로 저장하고 GitHub Actions가 PR을 생성·병합합니다.
7. 정기 실행은 월·수·금 UTC 22:00(KST 다음 날 오전 7시)이며, 적합한 주제가 없으면 발행하지 않습니다.

## 환경변수

- `OPENAI_API_KEY`: 콘텐츠 생성에 사용하는 OpenAI API 키
- `PUBLIC_CLOUDFLARE_WEB_ANALYTICS_TOKEN`: 로컬 웹 빌드용 선택 항목
- GitHub Actions에서는 `OPENAI_API_KEY`를 저장소 Secret으로, Cloudflare 토큰은 `CLOUDFLARE_WEB_ANALYTICS_TOKEN` 저장소 Variable로 등록합니다.

## 로컬 검증

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r bot/requirements.txt
python -m compileall -q bot
python bot/test_quality.py
python bot/main.py
```

웹 프로젝트는 다음과 같이 확인합니다.

```bash
cd web
npm ci
npm run test:work
npm run build
```

## 품질 정책

- 직접 출처 한 곳을 포함해 서로 다른 도메인의 출처를 두 곳 이상 확보합니다.
- 검색 결과의 개인 블로그·커뮤니티·복제 페이지는 근거에서 제외합니다.
- 핵심 사실 옆에 제공된 원문 URL을 연결하고 본문에서 출처를 두 개 이상 인용합니다.
- 사실과 편집 판단을 분리하고, 직접 사용하지 않은 제품을 사용해 본 것처럼 쓰지 않습니다.
- 제목의 과장 표현, 허위 1인칭 경험담, 제공되지 않은 수치와 URL을 차단합니다.
- 최근 글과 주제가 지나치게 비슷하면 발행하지 않습니다.
- 표, 복사 가능한 템플릿 또는 체크박스 중 하나 이상을 포함해 단순 요약을 넘어서는 실무 가치를 제공합니다.
- `30초 요약`, `확인된 사실`, `실무 판단`, `업무에 어떻게 쓸까`, `실행 체크리스트`, `한계와 주의점` 섹션을 요구합니다.
- 자동 품질검사는 사람의 사실 확인이나 제품 사용 테스트를 대신하지 않으며, 웹사이트에 생성 방식을 공개합니다.

## 사이트와 광고 설정

- 배포 주소: <https://fivejh.com>
- `ads.txt`: Astro의 `web/src/pages/ads.txt.ts` 한 곳에서 생성합니다.
- AdSense 게시자 레코드: `google.com, pub-1889114264117113, DIRECT, f08c47fec0942fa0`

전체 시각 규칙은 `DESIGN.md`를 참고합니다.
