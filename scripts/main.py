"""YouTube 자동 댓글 답글 — 단발 실행 엔진.

새 댓글을 확인하고, 내 과거 답글 말투를 학습한 AI가 답글안을 만들어,
dry-run(미리보기)이 기본값으로 동작한다. 실제 게시는 --no-dry-run 일 때만.

사용법:
    python scripts/main.py               # 1회 실행. dry-run 여부는 .env의 DRY_RUN (기본 true)
    python scripts/main.py --dry-run     # 강제 dry-run (미리보기만, 게시 안 함)
    python scripts/main.py --no-dry-run  # 실제 게시 1회
    python scripts/main.py --refresh-tone  # 말투 예시(few-shot)를 다시 수집

상시 실행(1시간마다 등)은 프로그램 안에 없다 — docs/always-on.md 부록 참고
(Windows 작업 스케줄러 / macOS launchd 로 이 스크립트를 반복 실행).
"""

import argparse
import json
import logging
import logging.handlers
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path

# --- 경로: 전부 스크립트 위치 기준 (하드코딩 금지) ---

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"
CLIENT_SECRET_PATH = BASE_DIR / "client_secret.json"
TOKEN_PATH = BASE_DIR / "token.json"
PROCESSED_PATH = BASE_DIR / "processed.json"
TONE_PATH = BASE_DIR / "tone_examples.json"
PROMPT_PATH = BASE_DIR / "prompts" / "auto-reply.md"
CHANNEL_PROFILE_PATH = BASE_DIR / "config" / "channel.md"
LOGS_DIR = BASE_DIR / "logs"

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Windows 콘솔(cp949)에서 한글 출력이 깨지지 않도록
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logger = logging.getLogger(__name__)

# --- 안전장치 상수 ---

CONSECUTIVE_SEEN_LIMIT = 3   # 이미 처리한 댓글이 연속 N개면 그 뒤는 전부 구댓글로 보고 조기 종료
FETCH_MAX_RESULTS = 30       # 한 번에 확인할 최근 댓글 수
TONE_EXAMPLES_IN_PROMPT = 10  # 프롬프트에 넣을 말투 예시 수


def setup_logging():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format)
    file_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(file_handler)


# --- 실행 전 점검 (친절한 한글 안내) ---


def preflight(channel_id: str) -> list:
    """실행에 필요한 준비물을 전부 점검하고 (문제, 해결법) 리스트 반환."""
    problems = []

    if not CLIENT_SECRET_PATH.exists():
        problems.append((
            "client_secret.json이 없습니다.",
            "docs/google-oauth.md 가이드를 따라 구글에서 발급받은 뒤,\n"
            f"           이 폴더에 넣어주세요: {BASE_DIR}",
        ))

    if not TOKEN_PATH.exists():
        problems.append((
            "아직 구글 계정 인증을 하지 않았습니다 (token.json 없음).",
            "client_secret.json을 넣은 뒤, Claude에게 \"인증해줘\"라고 말하거나\n"
            "           python scripts/auth_setup.py 를 실행하세요.",
        ))

    if not ENV_PATH.exists():
        problems.append((
            ".env 파일이 없습니다.",
            ".env.example을 복사해 .env를 만들어주세요.\n"
            "           Claude에게 \"세팅해줘\"라고 하면 자동으로 만들어줍니다.",
        ))
    elif not channel_id:
        problems.append((
            ".env에 YOUTUBE_CHANNEL_ID(내 채널 ID)가 비어 있습니다.",
            "\"인증해줘\"를 하면 인증 후 자동으로 채워집니다.\n"
            "           직접 확인하려면: 유튜브 스튜디오 → 설정 → 채널 → 고급 설정 → 채널 ID",
        ))

    if shutil.which("claude") is None:
        problems.append((
            "claude 명령을 찾을 수 없습니다 (답글 문장을 만드는 데 필요).",
            "Claude Code가 설치된 컴퓨터에서 실행해주세요. 터미널에서 claude --version 으로 확인할 수 있습니다.",
        ))

    return problems


def print_problems(problems: list):
    print()
    print("[준비가 필요합니다] 아직 실행할 수 없어요:")
    print()
    for i, (problem, fix) in enumerate(problems, 1):
        print(f"  {i}. {problem}")
        print(f"     → 해결: {fix}")
        print()
    print("준비가 끝나면 다시 \"답글 달아줘\"라고 말해주세요.")


# --- processed.json (처리 기록) ---


def load_processed() -> dict:
    if not PROCESSED_PATH.exists():
        return {"comment_ids": [], "video_comment_counts": {}}
    data = json.loads(PROCESSED_PATH.read_text(encoding="utf-8"))
    data.setdefault("comment_ids", [])
    data.setdefault("video_comment_counts", {})
    return data


def save_processed(data: dict):
    PROCESSED_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# --- 시스템 프롬프트 합성 ---


def build_system_prompt(tone_examples: list) -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")

    if tone_examples:
        examples_text = "\n".join(
            f'- 댓글: "{ex["comment"]}"\n  답글: "{ex["reply"]}"'
            for ex in tone_examples[:TONE_EXAMPLES_IN_PROMPT]
        )
    else:
        examples_text = "(아직 수집된 예시가 없습니다)"

    prompt = template.replace("{few_shot_examples}", examples_text)

    profile = ""
    if CHANNEL_PROFILE_PATH.exists():
        profile = CHANNEL_PROFILE_PATH.read_text(encoding="utf-8")

    return f"{prompt}\n\n---\n\n## 채널 프로필\n\n{profile}"


# --- 안전장치 필터 ---


def filter_new_comments(comments: list, processed_ids: set, owner_channel_id: str) -> list:
    """새 댓글만 필터링.

    안전장치:
    - 채널 소유자 본인이 쓴 댓글(고정 댓글 등)은 답글 대상에서 제외
    - 이미 처리한 댓글이 연속 CONSECUTIVE_SEEN_LIMIT개 나오면 조기 종료 (그 뒤는 전부 구댓글)
    """
    consecutive_seen = 0
    new_comments = []

    for comment in comments:
        if comment.get("author_channel_id") == owner_channel_id:
            continue
        if comment["id"] in processed_ids:
            consecutive_seen += 1
            if consecutive_seen >= CONSECUTIVE_SEEN_LIMIT:
                break
        else:
            consecutive_seen = 0
            new_comments.append(comment)

    return new_comments


def group_by_video(comments: list) -> dict:
    grouped = defaultdict(list)
    for c in comments:
        grouped[c["video_id"]].append(c)
    return dict(grouped)


# --- 말투 예시 (few-shot) ---


def ensure_tone_examples(service, channel_id: str, refresh: bool = False) -> list:
    from youtube_api import collect_tone_examples, load_tone_examples, save_tone_examples

    if not refresh:
        examples = load_tone_examples(TONE_PATH)
        if examples is not None:
            logger.info("기존 말투 예시 %d개 로드됨.", len(examples))
            return examples

    logger.info("내 과거 답글에서 말투 예시 수집 중... (최초 1회)")
    examples = collect_tone_examples(service, channel_id)
    save_tone_examples(examples, TONE_PATH)
    if examples:
        logger.info("말투 예시 %d개 수집 완료.", len(examples))
    else:
        logger.warning("수집된 과거 답글이 없습니다. 채널 프로필 설정만으로 진행합니다.")
    return examples


# --- 한 사이클 실행 ---


def process_cycle(service, system_prompt: str, channel_id: str, dry_run: bool, max_comments: int) -> dict:
    """한 번의 확인·답글 사이클. 결과 요약 dict 반환."""
    from llm import generate_replies_batch
    from youtube_api import (
        fetch_recent_comments,
        get_video_comment_count,
        get_video_info,
        post_reply,
    )

    summary = {"proposed": [], "posted": 0, "skipped_null": 0, "failed": 0, "new_comments": 0}

    processed = load_processed()
    processed_ids = set(processed["comment_ids"])
    video_comment_counts = processed["video_comment_counts"]

    logger.info("채널 댓글 확인 중...")
    comments = fetch_recent_comments(service, channel_id, max_results=max_comments)
    logger.info("가져온 최근 댓글: %d개", len(comments))

    if not comments:
        return summary

    new_comments = filter_new_comments(comments, processed_ids, channel_id)
    summary["new_comments"] = len(new_comments)
    logger.info("새 댓글: %d개", len(new_comments))

    if not new_comments:
        return summary

    grouped = group_by_video(new_comments)
    logger.info("영상 %d개에서 새 댓글 발견", len(grouped))

    done_ids = []

    for video_id, video_comments in grouped.items():
        # 안전장치: commentCount 캐시 — 댓글 수 변동이 없는 영상은 LLM 호출 없이 스킵 (API·사용량 절약)
        try:
            current_count = get_video_comment_count(service, video_id)
        except Exception:
            current_count = -1

        cached_count = video_comment_counts.get(video_id, 0)
        if current_count == cached_count and current_count >= 0:
            logger.info("[%s] 댓글 수 변동 없음 (%d개). 스킵.", video_id, current_count)
            done_ids.extend(c["id"] for c in video_comments)
            continue

        try:
            video_info = get_video_info(service, video_id)
        except Exception as e:
            logger.error("[%s] 영상 정보 조회 실패: %s", video_id, e)
            video_info = {"title": "", "description": ""}

        logger.info(
            "[%s] '%s' — 댓글 %d개에 대한 답글 생성 중...",
            video_id, video_info["title"][:30], len(video_comments),
        )

        replies = generate_replies_batch(
            system_prompt,
            video_info["title"],
            video_info["description"],
            video_comments,
        )

        if not replies:
            logger.warning("[%s] 답글 생성 실패. 다음 실행에서 다시 시도합니다.", video_id)
            continue

        video_failed = 0
        for reply_item in replies:
            idx = reply_item.get("index", 0) - 1  # 1-based → 0-based
            reply_text = reply_item.get("reply")

            if idx < 0 or idx >= len(video_comments):
                continue

            comment = video_comments[idx]

            if not reply_text:
                # null 답글 (스팸·무의미 댓글) → 답글 없이 처리 완료로 기록
                summary["skipped_null"] += 1
                done_ids.append(comment["id"])
                continue

            summary["proposed"].append({
                "video_title": video_info["title"],
                "author": comment["author"],
                "comment": comment["text"],
                "reply": reply_text,
            })

            if dry_run:
                done_ids.append(comment["id"])
            else:
                try:
                    reply_id = post_reply(service, comment["id"], reply_text)
                    logger.info("답글 게시 완료: %s → %s", comment["id"], reply_id)
                    summary["posted"] += 1
                    done_ids.append(comment["id"])
                except Exception as e:
                    logger.error("답글 게시 실패 [%s]: %s", comment["id"], e)
                    summary["failed"] += 1
                    video_failed += 1

        # 게시 실패가 있으면 캐시를 갱신하지 않는다 — 다음 실행에서 스킵되지 않고 재시도되도록
        if current_count >= 0 and video_failed == 0:
            video_comment_counts[video_id] = current_count

    # 기록 저장 — dry-run이면 저장하지 않는다 (실제 게시 전이므로 다음 실행에서 다시 잡힘)
    if dry_run:
        logger.info("[미리보기] 게시하지 않았으므로 처리 기록(processed.json)도 저장하지 않습니다.")
        return summary

    processed["comment_ids"] = list(processed_ids | set(done_ids))
    processed["video_comment_counts"] = video_comment_counts
    save_processed(processed)
    logger.info("처리 완료. 총 %d개 댓글 ID 기록됨.", len(processed["comment_ids"]))
    return summary


# --- 결과 출력 ---


def print_summary(summary: dict, dry_run: bool):
    line = "=" * 46
    print()
    print(line)
    if dry_run:
        print("  미리보기(dry-run) 결과 — 아직 아무것도 게시하지 않았습니다")
    else:
        print("  실행 결과")
    print(line)

    if summary["new_comments"] == 0:
        print("  새 댓글이 없습니다. 다음에 다시 확인해보세요.")
        print(line)
        return

    for i, p in enumerate(summary["proposed"], 1):
        print(f"\n  [{i}] 영상: {p['video_title'][:40]}")
        print(f"      댓글({p['author']}): {p['comment'][:80]}")
        print(f"      답글안: {p['reply']}")

    print()
    print(f"  답글안 {len(summary['proposed'])}개 · 건너뜀(스팸·무의미) {summary['skipped_null']}개", end="")
    if not dry_run:
        print(f" · 게시 성공 {summary['posted']}개 · 실패 {summary['failed']}개", end="")
    print()

    if dry_run:
        print("\n  실제로 게시하려면: python scripts/main.py --no-dry-run")
    print(line)


# --- 진입점 ---


def main():
    parser = argparse.ArgumentParser(description="YouTube 자동 댓글 답글 (1회 실행)")
    parser.add_argument(
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="미리보기만(게시 안 함). 기본값은 .env의 DRY_RUN (없으면 true).",
    )
    parser.add_argument(
        "--max-comments", type=int, default=FETCH_MAX_RESULTS,
        help=f"확인할 최근 댓글 수 (기본 {FETCH_MAX_RESULTS})",
    )
    parser.add_argument(
        "--refresh-tone", action="store_true",
        help="말투 예시(내 과거 답글)를 다시 수집",
    )
    args = parser.parse_args()

    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)

    channel_id = (os.getenv("YOUTUBE_CHANNEL_ID") or "").strip()

    # dry-run 우선순위: 명령 인자 > .env DRY_RUN > 기본 true (안전)
    if args.dry_run is None:
        dry_run = (os.getenv("DRY_RUN") or "true").strip().lower() == "true"
    else:
        dry_run = args.dry_run

    problems = preflight(channel_id)
    if problems:
        print_problems(problems)
        sys.exit(1)

    setup_logging()
    logger.info("실행 시작 (dry_run=%s, 채널=%s)", dry_run, channel_id)

    from youtube_api import get_youtube_service

    try:
        service = get_youtube_service(TOKEN_PATH)
    except Exception as e:
        print()
        print("[문제] 구글 인증 정보(token.json)를 읽지 못했습니다.")
        print(f"  원인: {e}")
        print("  → 해결: token.json 파일을 지우고, Claude에게 \"인증해줘\"라고 말해주세요.")
        sys.exit(1)

    tone_examples = ensure_tone_examples(service, channel_id, refresh=args.refresh_tone)
    system_prompt = build_system_prompt(tone_examples)

    try:
        summary = process_cycle(service, system_prompt, channel_id, dry_run, args.max_comments)
    except Exception as e:
        logger.error("실행 중 오류: %s", e, exc_info=True)
        print()
        print(f"[문제] 실행 중 오류가 났습니다: {e}")
        print("  → 해결: Claude에게 \"점검해줘\"라고 말해서 진단 결과를 확인해보세요.")
        sys.exit(1)

    print_summary(summary, dry_run)


if __name__ == "__main__":
    main()
