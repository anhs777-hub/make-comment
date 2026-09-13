"""Google OAuth 최초 인증 스크립트.

사전 준비 (docs/google-oauth.md 가이드 참고):
1. Google Cloud Console에서 프로젝트 생성 + YouTube Data API v3 사용 설정
2. OAuth 클라이언트 ID(데스크톱 앱) 생성 → client_secret.json 다운로드
3. client_secret.json을 make-comment 폴더(이 폴더의 상위)에 배치
4. 실행: python scripts/auth_setup.py → 브라우저 인증 → token.json 자동 저장

인증 후에는 내 채널 ID를 자동으로 확인해서 .env에 채워준다.
"""

import sys
from pathlib import Path

# Windows 콘솔·파이프(cp949)에서 한글 출력이 깨지지 않도록 (main.py와 동일)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
CLIENT_SECRET_PATH = BASE_DIR / "client_secret.json"
TOKEN_PATH = BASE_DIR / "token.json"
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


def update_env_channel_id(channel_id: str) -> str:
    """.env의 YOUTUBE_CHANNEL_ID를 채운다.

    Returns: "written"(새로 기입) | "same"(이미 같은 값) | "different"(다른 값이라 보존)
    """
    if not ENV_PATH.exists():
        if ENV_EXAMPLE_PATH.exists():
            ENV_PATH.write_text(ENV_EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            ENV_PATH.write_text("YOUTUBE_CHANNEL_ID=\nDRY_RUN=true\n", encoding="utf-8")

    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith("YOUTUBE_CHANNEL_ID="):
            found = True
            current = line.split("=", 1)[1].strip()
            if current == channel_id:
                return "same"
            if current:
                return "different"
            lines[i] = f"YOUTUBE_CHANNEL_ID={channel_id}"
            break
    if not found:
        lines.append(f"YOUTUBE_CHANNEL_ID={channel_id}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "written"


def main():
    if not CLIENT_SECRET_PATH.exists():
        print("[문제] client_secret.json이 없습니다.")
        print("  → 해결: docs/google-oauth.md 가이드를 따라 발급받은 뒤,")
        print(f"          이 폴더에 넣어주세요: {BASE_DIR}")
        sys.exit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_PATH), SCOPES)

    print("잠시 후 브라우저가 열립니다.")
    print("유튜브 채널을 운영하는 구글 계정으로 로그인하고 '허용'을 눌러주세요.")
    print("('Google에서 확인하지 않은 앱' 경고가 나오면: 고급 → 이동 을 누르면 됩니다. 본인이 만든 앱이라 안전합니다.)")

    credentials = flow.run_local_server(
        port=0,
        authorization_prompt_message="",
        success_message="인증이 완료되었습니다! 이 창은 닫고, Claude Code 화면으로 돌아가세요.",
    )

    TOKEN_PATH.write_text(credentials.to_json(), encoding="utf-8")
    print("인증 완료! token.json이 저장되었습니다.")

    # 채널 ID 자동 확인 + .env 기입
    try:
        service = build("youtube", "v3", credentials=credentials)
        response = service.channels().list(part="id,snippet", mine=True).execute()
        items = response.get("items", [])
    except Exception as e:
        print(f"[안내] 채널 정보 확인 중 오류가 났지만, 인증 자체는 완료됐습니다: {e}")
        return

    if not items:
        print("[안내] 이 구글 계정에 유튜브 채널이 없습니다.")
        print("  → 유튜브 채널이 있는 계정으로 다시 인증해주세요. (token.json을 지우고 재실행)")
        return

    channel_id = items[0]["id"]
    channel_title = items[0]["snippet"]["title"]
    print(f"인증된 채널: {channel_title} ({channel_id})")

    result = update_env_channel_id(channel_id)
    if result == "written":
        print(".env에 채널 ID를 자동으로 채웠습니다. 준비 끝!")
    elif result == "same":
        print(".env의 채널 ID가 이미 올바르게 설정되어 있습니다.")
    else:  # different
        print("[주의] .env에 적힌 YOUTUBE_CHANNEL_ID가 방금 인증한 채널과 다릅니다.")
        print(f"  → 내 채널이 맞는지 확인하고, .env 값을 {channel_id} 로 바꿔주세요.")


if __name__ == "__main__":
    main()
