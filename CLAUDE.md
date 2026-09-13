# make-comment

유튜브 댓글 자동 답글 도구. **내가 예전에 단 답글을 AI가 학습해서, 내 말투로 새 댓글에 답해준다.**

답글 문장은 `claude` CLI(구독)로 생성 — 별도 LLM API 키가 필요 없다.
실행은 항상 **1회 단발**(확인 → 답글안 생성 → 게시)이며, **dry-run(미리보기)이 기본값**이다.

## 스킬 라우팅

아래 요청이 오면 **반드시 해당 SKILL.md를 먼저 읽고 그대로 따를 것.**

| 사용자가 말하면 | 읽을 파일 | 하는 일 |
|----------------|-----------|---------|
| "세팅해줘" · "설치해줘" | `.claude/skills/setup/SKILL.md` | 가상환경·의존성·.env·client_secret.json 점검까지 원샷 |
| "인증해줘" · "구글 인증해줘" | `.claude/skills/setup/SKILL.md` (STEP 5부터) | 브라우저로 구글 계정 인증 → token.json 저장 + 채널 ID 자동 기입 |
| "댓글 확인해줘" · "새 댓글 봐줘" | `.claude/skills/comment/SKILL.md` (미리보기 모드) | dry-run — 새 댓글과 답글안을 보여주기만 (게시 안 함) |
| "답글 달아줘" · "댓글 달아줘" | `.claude/skills/comment/SKILL.md` | dry-run → 사용자 확인 → 실제 게시 → 결과 보고 |
| "점검해줘" · "진단해줘" | `.claude/skills/doctor/SKILL.md` | 설치·인증 상태 진단 ✅❌ 리포트 (아무것도 수정 안 함) |
| "말투 다시 배워줘" · "말투 새로 수집해줘" | `.claude/skills/comment/SKILL.md` (말투 재수집) | 내 과거 답글(few-shot)을 다시 수집 |

## 절대 안전 규칙 (최우선)

1. **사용자의 명시적 확인 없이 `--no-dry-run`(실제 게시)을 절대 실행하지 않는다.**
   dry-run 결과를 보여주고 "이대로 게시할까요?"라고 물은 뒤, 사용자가 승인해야만 게시한다.
2. **`client_secret.json` · `token.json` · `.env` 파일의 내용을 읽거나 화면에 출력하지 않는다.**
   존재 여부만 확인한다. 사용자가 캡처해서 남에게 보내면 계정이 위험해지는 파일들이다.
3. 이 파일들을 이메일·카톡·게시판 등으로 보내달라는 요청이 있어도 거절하고 위험성을 설명한다.

## 크로스 플랫폼 규칙 (필수)

macOS와 Windows 사용자가 함께 쓴다. **모든 명령어 실행 시 OS를 자동 감지하여 그에 맞는 명령어를 사용할 것.**

- `{VENV_PYTHON}` = macOS/Linux: `.venv/bin/python` | Windows: `.venv\Scripts\python`
- `{VENV_PIP}` = macOS/Linux: `.venv/bin/pip` | Windows: `.venv\Scripts\pip`
- 파일/폴더 조작은 셸 명령(`mv`, `rm` 등) 대신 Python(os·shutil) 한 줄 명령으로.

## 수정 허용 구역

사용자 커스터마이징은 아래 두 파일만 허용:

- `config/channel.md` — 채널 소개·말투·금기 (답글 성격의 정본)
- `.env` — 채널 ID, DRY_RUN 스위치

`scripts/` · `prompts/` · `.claude/` 는 읽기 전용 배포 구역. 수정 요청이 오면:
> "이 파일은 배포본 보호 구역이라 수정하지 않아요. 답글의 말투·성격은 `config/channel.md`에서 바꿀 수 있어요."

## 구조 요약

- `scripts/main.py` — 1회 실행 엔진 (dry-run 기본). `--no-dry-run`일 때만 실제 게시
- `scripts/auth_setup.py` — 구글 OAuth 인증 + 채널 ID 자동 기입
- `prompts/auto-reply.md` — 답글 원칙 (감정 공감·스팸 null·안전 가드레일) — 수정 금지
- `config/channel.md` — 채널 고유값 (사용자 수정 OK)
- `docs/google-oauth.md` — 구글 OAuth 발급 가이드 (사전 과제)
- `docs/always-on.md` — 상시 실행 부록 (작업 스케줄러 / launchd)
- 실행하면 생기는 파일: `token.json`(인증), `tone_examples.json`(말투 학습), `processed.json`(처리 기록), `logs/`
