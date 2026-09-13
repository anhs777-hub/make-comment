---
name: setup
description: 환경 세팅 스킬. OS 감지 → 폴더 위치 점검 → Python 가상환경 → 의존성 설치 → .env 생성 → client_secret.json 확인 → 구글 인증(auth_setup.py) → ✅ 체크리스트. 트리거: "세팅해줘", "설치해줘", "인증해줘", "setup".
---

# Setup Skill

압축을 막 푼 폴더를 "답글 달아줘"가 가능한 상태로 만든다.
**여러 번 실행해도 안전하다** — 이미 완료된 단계는 확인만 하고 넘어간다.

`{PY}` = 시스템 Python (STEP 0에서 결정) · `{VENV_PYTHON}`·`{VENV_PIP}` = CLAUDE.md 크로스 플랫폼 규칙 참조

**"인증해줘"로 들어왔으면 STEP 5부터 시작한다** (앞 단계는 빠르게 확인만).

## 원칙

- 파일/폴더 조작은 셸 명령 대신 **Python(os·shutil)** — CLAUDE.md 크로스 플랫폼 규칙
- 각 STEP 결과를 한 줄씩 보고하며 진행, 마지막에 ✅ 체크리스트로 종합
- `client_secret.json`·`token.json`·`.env`의 **내용은 절대 읽거나 출력하지 않는다** (존재 여부만)

## STEP 0. OS·Python 확인

1. OS는 실행 환경에서 감지 (macOS / Windows)
2. 시스템 Python 찾기 — `python --version` → `python3 --version` → (Windows) `py --version` 순서로 시도, 처음 성공하는 것이 `{PY}`
3. 3.10 미만이거나 Python이 없으면 **중단**하고 안내:
   > Python 설치가 필요합니다. python.org에서 설치하세요. **Windows는 설치 첫 화면에서 "Add python.exe to PATH"를 반드시 체크**하세요. 설치 후 VS Code를 완전히 껐다 켜고 다시 "세팅해줘"라고 해주세요.

## STEP 1. 폴더 위치 점검

```
{PY} -c "import os; p=os.getcwd(); print('PATH:', p); print('ROOT:', 'OK' if os.path.exists('CLAUDE.md') and os.path.exists('VERSION') else 'MISSING'); print('NESTED:', 'YES' if os.path.exists(os.path.join('make-comment','CLAUDE.md')) else 'NO'); print('ASCII:', 'OK' if p.isascii() else 'NON_ASCII'); print('ONEDRIVE:', 'YES' if 'onedrive' in p.lower() else 'NO')"
```

| 결과 | 대응 |
|------|------|
| ROOT MISSING + NESTED YES | 이중 폴더 — "VS Code에서 안쪽 `make-comment` 폴더를 다시 열고 '세팅해줘'를 해주세요" 안내 후 중단 |
| ROOT MISSING + NESTED NO | 잘못된 폴더 — "압축을 푼 `make-comment` 폴더 자체를 여세요" 안내 후 중단 |
| NON_ASCII 또는 ONEDRIVE | 한글 경로·OneDrive는 오류의 원인 — 이동 목표(macOS `~/make-comment` / Windows `C:\make-comment`)를 알리고 **동의받은 뒤** `shutil.move`(macOS) / `shutil.copytree`(Windows)로 이동, 새 위치에서 다시 열도록 안내 후 중단 |
| 모두 정상 | STEP 2로 |

## STEP 2. 가상환경(.venv)

- `.venv` 없음 → `{PY} -m venv .venv`
- 있음 → `{VENV_PYTHON} --version` 실행 확인. 실패하면(다른 OS·컴퓨터에서 만든 .venv 등) 지우고 재생성

## STEP 3. 의존성 설치

```
{VENV_PIP} install -U -r requirements.txt
```

확인: `{VENV_PYTHON} -c "import googleapiclient, google_auth_oauthlib, dotenv; print('OK')"`

## STEP 4. .env 준비

- `.env` 없으면 `.env.example`을 복사해 생성:
  `{PY} -c "import shutil, os; os.path.exists('.env') or shutil.copy('.env.example', '.env'); print('OK')"`
- `YOUTUBE_CHANNEL_ID`는 비워둬도 된다 — STEP 5 인증이 자동으로 채운다

## STEP 5. client_secret.json 확인 (사전 과제)

존재 확인만: `{PY} -c "import os; print('OK' if os.path.exists('client_secret.json') else 'MISSING')"`

- **MISSING이면**: 여기서 인증 진행 불가. 안내 후 나머지 STEP은 ❌로 기록하고 체크리스트로:
  > 구글에서 발급받는 `client_secret.json` 파일이 필요합니다 (수업 사전 과제).
  > `docs/google-oauth.md` 가이드를 따라 발급받아 이 폴더에 넣은 뒤, "인증해줘"라고 말해주세요.
- 있으면 STEP 6으로

## STEP 6. 구글 인증 (브라우저)

`token.json`이 이미 있으면 "이미 인증되어 있습니다"라고 알리고 STEP 7로.

없으면 사용자에게 예고부터:
> 이제 브라우저가 열립니다. 유튜브 채널을 운영하는 구글 계정으로 로그인하고 '허용'을 눌러주세요.
> "Google에서 확인하지 않은 앱" 경고가 나오면 → 고급 → 이동. (본인이 만든 앱이라 안전합니다)

```
{VENV_PYTHON} scripts/auth_setup.py
```

- 성공하면 스크립트가 채널 이름·채널 ID를 출력하고 `.env`에 자동 기입한다
- "403" 또는 "액세스 차단됨" 오류 → docs/google-oauth.md의 "자주 막히는 곳" 표 안내 (테스트 사용자 미등록이 대부분)

## STEP 7. 채널 프로필 (선택)

`config/channel.md`가 아직 "(내 채널 이름을 적어주세요)" 템플릿 그대로면:
- 채널 이름·다루는 주제·원하는 말투 2~3가지를 대화로 물어보고 `config/channel.md`를 채워준다
- 사용자가 "나중에"라고 하면 그대로 두고 진행 (없어도 동작한다)

## STEP 8. ✅ 체크리스트 출력 (고정 양식)

```
✅ 세팅 완료 — make-comment v{VERSION}
──────────────────────────────
✅ OS               : macOS
✅ 폴더 위치         : /Users/xxx/make-comment
✅ Python           : 3.12.4 (.venv)
✅ 의존성            : google-api-python-client 외 2종
✅ .env             : 준비됨 (DRY_RUN=true)
✅ client_secret    : 있음
✅ 구글 인증         : 완료 (채널: 내 채널 이름)
──────────────────────────────
다음 단계: "댓글 확인해줘" (미리보기) → "답글 달아줘"
```

- 버전은 루트 `VERSION` 파일에서 읽는다
- ❌가 하나라도 있으면 마지막 줄을 다음으로 교체:
  > ❌ 항목이 있습니다. **이 화면을 캡처해서 조교에게 보내주세요.** 가장 빠른 해결 방법입니다.
  > (단, client_secret.json·token.json 파일 내용은 절대 캡처하지 마세요!)
