# Changelog — make-comment

> 오토워커 2기 3강 배포 프로젝트. 유튜브 댓글 자동 답글 도구.

## v1.0.0 (2026-08-21)

**최초 배포판.** 개인용 make-comment 봇을 수강생 배포용으로 재구성.

원본 대비 주요 변경:

- **단발 실행이 기본** — 상시 루프(8~23시 정각) 제거, "답글 달아줘" 1회 = 확인·게시 1회.
  상시 실행은 `docs/always-on.md` 부록(작업 스케줄러/launchd)으로 분리
- **dry-run(미리보기) 기본 + 사용자 확인 후 게시** 스킬 흐름
- **채널 ID 하드코딩 제거** — 미설정 시 한글 안내, 인증(auth_setup.py) 시 자동 기입
- **경로 전부 스크립트 위치 기준** — 어느 폴더에 놓아도 동작, logs/ 자동 생성
- 답글 프롬프트를 감정 공감 원칙판(`prompts/auto-reply.md`)으로 교체,
  채널 고유값은 `config/channel.md`로 분리
- 안전장치 이식: 연속 기존댓글 조기 종료, 영상별 commentCount 캐시(API 절약), 본인 댓글 제외
- 스킬 3종(setup/comment/doctor) + 트리거 표(CLAUDE.md) + 구글 OAuth 텍스트 가이드 신설
- OAuth 스코프는 `youtube.force-ssl` 1개 유지
- 배포 전 최종 점검: auth_setup.py에도 UTF-8 출력 가드 추가(Windows cp949 깨짐 방지), status.ps1 실행 안내에 ExecutionPolicy 우회 명령 명시
