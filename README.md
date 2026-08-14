# my-auto-blog

RSS와 웹 검색 결과를 근거로 Gemini가 기술 글을 만들고, 검증된 글만 Astro 블로그에 발행하는 자동화 저장소입니다.

## 실행 흐름

1. GeekNews와 Hacker News RSS를 타임아웃 및 HTTP 상태 검사와 함께 수집합니다.
2. `ddgs` 검색 결과를 보완 자료로 추가하고 HTTP(S) 원문 URL을 중복 제거합니다.
3. `generateContent`를 지원하는 안정 Gemini 텍스트 모델로 Markdown을 생성합니다.
4. 제목, 요약, 태그, 본문 길이, 출처와 허용되지 않은 URL을 검사합니다.
5. 검증된 원문 URL로 `## 참고자료`를 추가한 뒤 글을 저장합니다.
6. GitHub Actions가 PR을 만들고 즉시 squash merge한 다음 같은 실행에서 Pages에 배포합니다.

품질검사나 생성이 실패하면 Markdown을 저장하지 않으며 워크플로도 실패합니다.

## 환경변수

- `GEMINI_API_KEY` (필수): Google Gemini API 키
- `GEMINI_MODEL` (선택): 우선 사용할 안정 텍스트 모델. 저장소 Actions 변수 또는 로컬 환경변수로 설정합니다. 호환되지 않으면 자동으로 무시됩니다.

GitHub 저장소에는 `GEMINI_API_KEY`를 Actions secret으로 등록해야 합니다. 자동 PR 생성과 병합에는 워크플로의 `contents: write`, `pull-requests: write` 권한이 사용됩니다.

## 로컬 실행 및 검증

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r bot/requirements.txt
python -m compileall -q bot
python bot/test_quality.py
python bot/main.py
```

웹 프로젝트도 함께 확인하려면 다음을 실행합니다.

```bash
cd web
npm ci
npm run build
```

## 품질 정책

- Google 모델 목록에서 `generateContent` 지원이 확인된 allowlist 모델만 사용합니다.
- audio, image, embedding, TTS, live, preview, experimental, Omni 계열은 사용하지 않습니다.
- 제목과 요약에 생성 실패 문구가 없어야 하고, 최종 태그는 3개 이상이어야 합니다.
- 참고자료를 제외한 본문은 3,500자 이상이어야 합니다.
- RSS 또는 검색 결과에서 확인한 HTTP(S) URL이 하나 이상 있어야 합니다.
- 모델이 제공받지 않은 URL을 본문에 넣으면 발행을 차단합니다.
- 실제 경험으로 오인될 수 있는 1인칭 경험담과 근거 없는 회사 사례를 차단합니다.
- 확인되지 않은 제품명, 모델명, 출시 정보, 수치, 성능을 단정하지 않도록 프롬프트에서 제한합니다.

자동화 PR은 작성자 자신이 승인하는 방식이 아닙니다. 품질검사를 통과한 PR을 워크플로가 즉시 병합합니다. 나중에 `main` 보호 규칙에서 승인을 필수로 설정하면 자동 병합 단계가 실패하도록 되어 있어 검토 없이 발행되지 않습니다.
