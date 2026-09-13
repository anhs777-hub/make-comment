# 심화 부록: 상시 자동 실행

> **기본 사용법은 이 문서가 필요 없습니다.** "답글 달아줘" 한 번 = 확인·게시 1회가 기본입니다.
> 이 문서는 "컴퓨터가 1시간마다 알아서 답글을 달게" 하고 싶은 분을 위한 심화 내용입니다.

## 시작하기 전에 (꼭 읽어주세요)

상시 실행은 **미리보기 없이 자동으로 게시**됩니다. 그래서:

1. 먼저 **"답글 달아줘"를 여러 번 써보면서** 답글 품질이 마음에 드는지 충분히 확인하세요
2. `config/channel.md`의 말투·금지 규칙을 다듬어 두세요
3. 언제든 중단할 수 있게 아래 "끄는 법"도 같이 알아두세요

원리: `scripts/main.py`는 1회 실행하고 끝나는 프로그램입니다.
운영체제의 예약 기능(작업 스케줄러/launchd)이 이걸 주기적으로 다시 실행해주는 방식입니다.

실행 명령에는 `--no-dry-run`이 필요합니다 (없으면 미리보기만 하고 게시하지 않습니다 — 안전 기본값).

---

## Windows — 작업 스케줄러

1. 시작 메뉴에서 **"작업 스케줄러"** 검색 → 실행
2. 오른쪽 **"기본 작업 만들기"** 클릭
3. 이름: `make-comment 자동 답글` → 다음
4. 트리거: **"매일"** 선택 → 다음 → 시작 시간 예: 오전 9:00 → 다음
5. 작업: **"프로그램 시작"** → 다음
6. 아래처럼 입력 (폴더 위치는 본인 것으로 바꾸세요. 예: `C:\make-comment`):
   - **프로그램/스크립트**: `C:\make-comment\.venv\Scripts\python.exe`
   - **인수 추가**: `C:\make-comment\scripts\main.py --no-dry-run`
   - **시작 위치**: `C:\make-comment`
7. 마침 → 만든 작업을 더블클릭 → **"트리거"** 탭 → 편집 →
   **"작업 반복 간격"** 체크 → `1시간`, 기간 `12시간` (밤에는 안 돌게) → 확인

확인: 작업을 마우스 오른쪽 클릭 → "실행" → `logs\bot.log`에 기록이 남는지 확인.
상태 화면: PowerShell을 열고 아래를 입력 (최근 로그·실행 여부·중지 메뉴):

```
powershell -ExecutionPolicy Bypass -File C:\make-comment\scripts\status.ps1
```

(그냥 `scripts\status.ps1`로 실행하면 Windows 기본 보안 설정이 "스크립트 실행 사용 안 함"
오류를 낼 수 있어, 위처럼 실행하는 것이 안전합니다.)

**끄는 법**: 작업 스케줄러에서 해당 작업 오른쪽 클릭 → "사용 안 함" 또는 "삭제".

## macOS — launchd

1. 터미널에서 설정 파일 생성 (폴더 위치 두 곳을 본인 경로로 바꾸세요):

```bash
cat > ~/Library/LaunchAgents/com.make-comment.reply.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.make-comment.reply</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/내이름/make-comment/.venv/bin/python</string>
    <string>/Users/내이름/make-comment/scripts/main.py</string>
    <string>--no-dry-run</string>
  </array>
  <key>StartInterval</key>
  <integer>3600</integer>
  <key>WorkingDirectory</key>
  <string>/Users/내이름/make-comment</string>
</dict>
</plist>
EOF
```

2. 등록: `launchctl load ~/Library/LaunchAgents/com.make-comment.reply.plist`
3. 확인: 1시간 뒤 `logs/bot.log`에 기록이 남는지 확인
   (바로 시험하려면: `launchctl start com.make-comment.reply`)

**끄는 법**: `launchctl unload ~/Library/LaunchAgents/com.make-comment.reply.plist`

---

## 참고

- 하루 유튜브 API 무료 한도는 10,000 단위 — 1시간 간격 실행이면 넉넉합니다
  (댓글 수가 안 변한 영상은 건너뛰는 절약 장치가 들어 있습니다)
- 답글 생성에는 컴퓨터가 켜져 있고 Claude Code(claude 명령)가 로그인된 상태여야 합니다
- 설정이 어렵게 느껴지면 그냥 기본 방식(생각날 때 "답글 달아줘")을 쓰세요 — 그걸로 충분합니다
