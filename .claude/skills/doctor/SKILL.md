---
name: doctor
description: 설치·인증 상태 진단 스킬. 폴더·버전·가상환경·의존성·자격증명·claude CLI·파일 무결성(manifest 대조)을 검사해 ✅❌ 리포트를 출력한다. 진단 전용 — 어떤 파일도 수정하지 않음. 트리거: "점검해줘", "진단해줘", "상태 확인해줘", "doctor".
---

# Doctor Skill

설치·인증 문제를 한 번에 진단한다. 리포트 캡처 → 조교 전달이 CS의 1차 프로토콜이다.

## 원칙

- **진단만 한다. 파일을 만들거나 고치거나 지우지 않는다.** 고치는 것은 "세팅해줘"/"인증해줘"의 몫
- 검사 중간에 ❌가 나와도 **끝까지 전부 검사**하고 종합 리포트를 낸다
- 검사는 Python 한 줄 명령으로 (CLAUDE.md 크로스 플랫폼 규칙). `.venv`가 없거나 깨진 상태면 시스템 python으로 검사
- `client_secret.json`·`token.json`·`.env`는 **존재 여부만** 확인 — 내용을 읽거나 출력하지 않는다

## 검사 항목 (7종, 순서대로)

### 1. 폴더
- `CLAUDE.md`·`VERSION` 존재 확인. 없으면 ❌ 잘못된 폴더:
  - 하위에 `make-comment/CLAUDE.md`가 있으면 → 비고: "이중 폴더 — VS Code에서 안쪽 폴더를 여세요"
- 현재 경로에 비ASCII(한글) 또는 OneDrive 포함 → ⚠️ 비고: "'세팅해줘'가 이동을 도와줍니다"

### 2. 버전
- `VERSION` 값 읽기
- `CHANGELOG.md` 최상단 `## v…` 섹션의 버전과 일치하는지 (불일치 → ⚠️ 파일 오염 의심)

### 3. Python·가상환경
- `.venv` 존재 + `{VENV_PYTHON} --version` 실행 성공 + 3.10 이상
- 실패 → ❌ 비고: "'세팅해줘'를 실행하세요" (다른 OS에서 만든 .venv가 복사된 경우도 세팅해줘가 재생성)

### 4. 의존성
- `{VENV_PYTHON} -c "import googleapiclient, google_auth_oauthlib, dotenv; print('OK')"`
- 실패 → ❌ 비고: "'세팅해줘'를 실행하세요"

### 5. 자격증명 (존재 여부만!)
```
{VENV_PYTHON} -c "import os; print('SECRET:', 'OK' if os.path.exists('client_secret.json') else 'MISSING'); print('TOKEN:', 'OK' if os.path.exists('token.json') else 'MISSING'); print('ENV:', 'OK' if os.path.exists('.env') else 'MISSING')"
```
- `.env`가 있으면 채널 ID 설정 여부만 추가 확인 (값은 채널 ID라 공개 정보 — 표시해도 됨):
  `{VENV_PYTHON} -c "from dotenv import dotenv_values; v=dotenv_values('.env'); print('CHANNEL:', v.get('YOUTUBE_CHANNEL_ID') or 'EMPTY'); print('DRY_RUN:', v.get('DRY_RUN'))"`
- SECRET MISSING → ❌ 비고: "docs/google-oauth.md 가이드로 발급 (수업 사전 과제)"
- TOKEN MISSING → ❌ 비고: "'인증해줘'를 실행하세요"
- CHANNEL EMPTY → ⚠️ 비고: "'인증해줘'가 자동으로 채워줍니다"

### 6. claude CLI
- `claude --version` (또는 Windows에서 `claude.cmd --version`)
- 실패 → ❌ 비고: "Claude Code 설치 상태 확인 필요 — 조교에게 문의"

### 7. 파일 무결성 (manifest 대조)
- 아래 Manifest 블록의 경로 전부를 Python으로 일괄 존재 확인:
```
{VENV_PYTHON} -c "import os; paths=['CLAUDE.md','README.md', ...manifest 전체...]; miss=[p for p in paths if not os.path.exists(p)]; print('OK' if not miss else 'MISSING: '+', '.join(miss))"
```
- 누락 → ❌ 비고: "배포 zip을 다시 받아 누락 파일을 복사하세요 (token.json·.env 등 내 파일은 그대로 두면 됩니다)"

### Manifest (정본 — 배포 규격 검사 packager도 이 블록을 파싱한다)

```manifest
CLAUDE.md
README.md
CHANGELOG.md
VERSION
requirements.txt
.env.example
.gitignore
.claude/skills/setup/SKILL.md
.claude/skills/comment/SKILL.md
.claude/skills/doctor/SKILL.md
scripts/main.py
scripts/youtube_api.py
scripts/llm.py
scripts/auth_setup.py
scripts/status.ps1
prompts/auto-reply.md
config/channel.md
docs/google-oauth.md
docs/always-on.md
```

## 리포트 (고정 양식)

```
🩺 점검 결과 — make-comment v1.0.0

| 항목 | 상태 | 비고 |
|------|------|------|
| 폴더 위치 | ✅ | C:\make-comment |
| 버전 | ✅ | v1.0.0 (CHANGELOG 일치) |
| Python 가상환경 | ✅ | Python 3.12.4 |
| 의존성 | ✅ | 3종 정상 |
| 자격증명 | ✅ | client_secret ○ / 인증 ○ / 채널 ID ○ (DRY_RUN=true) |
| claude CLI | ✅ | 2.x |
| 파일 무결성 | ✅ | 19/19 |
```

- 전부 ✅ → 마지막 줄: "모든 항목 정상입니다. '댓글 확인해줘' 또는 '답글 달아줘' 하시면 됩니다."
- ❌/⚠️ 있음 → 마지막 줄 고정 (생략 금지 — CS 1차 프로토콜):
  > **이 결과 화면을 캡처해서 조교에게 보내주세요.** 가장 빠른 해결 방법입니다.
  > (client_secret.json·token.json 파일의 내용은 절대 캡처하거나 보내지 마세요 — 계정 열쇠입니다!)
