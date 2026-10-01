# 네일 트랜스퍼 실험실

사용자 손 사진과 네일 디자인 참고 사진을 올리면 YouCam **AI Nail Transfer** 결과를 보여주는 로컬 Streamlit 웹앱입니다. 
피부 퍼스널 컬러 분석, 회원 가입, DB, 배포는 이 버전의 범위에 포함하지 않습니다.

## 기획

| 항목 | 결정 |
| --- | --- |
| 문제 | 네일 디자인이 내 손에 어울리는지 실제 시술 전 확인하기 어렵다 |
| 대상 | 내 손 사진과 참고 디자인 사진을 가진 개인 사용자 |
| 핵심 흐름 | 두 장 업로드 → 유효성 검사 → YouCam 업로드 → 작업 요청 → 완료 조회 → 결과 표시·저장 |
| 성공 기준 | 로컬 웹에서 실제 API 응답 이미지를 확인하고 다운로드할 수 있다 |
| 제외 | 퍼스널 컬러 탐지, 디자인 생성, 회원·이력·DB, 모바일 최적화 |

여기서 **아트 에셋**은 임의의 투명 PNG 스티커가 아니라, 네일 디자인이 보이는 *참고 사진*입니다. 
AI Nail Transfer의 필수 입력인 `ref_file_id`로 전달합니다. 원하는 색·손가락·패턴을 별도로 지정하는 편집 기능은 이번 API 호출의 범위 밖입니다. 
공식 API는 최대 두 손을 처리하며 손톱이 선명한 사진을 권장합니다.

## 로컬 실행 (VS Code 터미널)

Python 3.10 이상이 필요합니다. 프로젝트 폴더에서:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
uv python install 3.12
uv venv --python 3.12
uv pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

YouCam [API 콘솔](https://yce.makeupar.com/api-console/en/api-keys/)에서 발급받은 키를 `.env`의 `YOUCAM_API_KEY` 값에 넣은 후:

```bash
streamlit run app.py
```

브라우저의 로컬 주소(기본 `http://localhost:8501`)에서 손 사진과 네일 디자인 참고 사진을 업로드하고 **네일 적용하기**를 누릅니다.   
결과 처리는 비동기이므로 최대 약 3분간 10초 간격으로 조회합니다.  
시간이 초과하면 화면에 작업 ID를 표시합니다. 
다시 버튼을 누르면 새 작업을 만들므로 사용량이 추가될 수 있습니다.   
이미 성공해 다운로드한 이미지는 현재 브라우저 세션 메모리에만 보관됩니다.   
`.env`를 Git에 커밋하지 마세요.

## 구조

```text
app.py                          Streamlit 화면, 입력·결과 표시
nail_lab/domain/images.py       이미지 형식·크기 규칙, 입력 모델
nail_lab/application/ports.py   외부 API 포트 (Protocol)
nail_lab/application/transfer.py 사용 사례와 상태 전이
nail_lab/adapters/youcam.py     YouCam HTTP 어댑터
tests/                          가짜 게이트웨이로 흐름 검증
```

하프 헥사고날 구성입니다. UI가 애플리케이션 서비스를 호출하고, 서비스는 외부 API 포트만 압니다. 
인바운드 HTTP 서버나 데이터베이스 추상화는 만들지 않습니다. 
Streamlit 프로세스가 로컬 웹 서버 역할을 하므로 FastAPI를 별도로 띄울 필요가 없습니다.

## 외부 API와 제한

- `POST /s2s/v2.0/file`: 파일명·크기·MIME을 보내 업로드 URL과 `file_id`를 받습니다. 반환된 서명 URL에 각각 `PUT`으로 실제 바이트를 올립니다.
- `POST /s2s/v2.0/task/ai-nail`: `src_file_id`와 `ref_file_id`로 작업을 만들고 `task_id`를 받습니다.
- `GET /s2s/v2.0/task/ai-nail/{task_id}`: `running`, `success`, `error`를 확인합니다. 

성공 시 `data.results.url`의 결과를 바로 다운로드해 세션에 표시합니다.

API 인증은 서버 쪽 Python에서만 수행합니다.  
서명 업로드 URL에는 API 키를 전달하지 않습니다.   
이미지와 결과는 YouCam 측 서비스로 전송되므로 본인에게 업로드 권한이 있는 사진만 사용하세요.   
공식 문서의 이 기능은 작업당 1 unit을 소비합니다.  
결과 URL은 유효 기간이 제한되므로 완료 즉시 이미지를 내려받습니다.  
실제 동작과 계정별 과금·잔여량은 발급받은 키로 확인해야 합니다.

키는 YouCam AI API에서 별도로 발급받으셔야 합니다. 

실패 시 401은 키, 429는 호출 제한, 
`no_hand_detected`는 손 사진, `error_download_image`는 업로드를 우선 점검하세요. API 측 오류 문구는 화면에 표시합니다.

## 테스트

```bash
python -m unittest discover -s tests -v
```
## 모바일 기기 활용시 
서버 구동후 나오는 streamlit network 주소로 접속해서 사용하시면 됩니다. 

공식 자료:   
[AI Nail Transfer](https://docs.perfectcorp.com/reference/ai_nail_transfer) 
[OpenAPI 명세](https://docs.perfectcorp.com/_bundle/reference/ai_nail_transfer.json?download=), 
[파일 업로드 예시](https://docs.perfectcorp.com/reference/ai_clothes/section/overview), 
[API Playground](https://yce.perfectcorp.com/api-console/en/api-playground/ai-nail-transfer/)

** 해당 프로젝트는 YouCam AI API 무료 크레딧을 제공받아 테스트를 진행하였습니다 **