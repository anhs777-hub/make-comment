"""claude CLI 호출 래퍼: 영상별 배치로 답글 생성.

API 키 없이 Claude 구독(claude CLI)으로 답글을 생성한다.
- Claude Code 안에서 실행돼도 동작하도록 CLAUDECODE 환경변수를 제거한다.
- Windows 콘솔(cp949)에서도 깨지지 않도록 utf-8을 명시한다.
"""

import json
import logging
import os
import platform
import re
import subprocess

logger = logging.getLogger(__name__)

CLAUDE_TIMEOUT = 180  # 초. 느린 노트북 대비 여유


def _extract_json_array(text: str) -> str:
    """LLM 응답에서 JSON 배열 부분만 추출."""
    # ```json ... ``` 블록 추출
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()

    # [ ... ] 배열 직접 추출
    m = re.search(r"(\[.*\])", text, re.DOTALL)
    if m:
        return m.group(1).strip()

    return text.strip()


def generate_replies_batch(
    system_prompt: str,
    video_title: str,
    video_desc: str,
    comments: list,
) -> list:
    """한 영상의 모든 댓글에 대해 한 번에 답글 생성.

    Args:
        system_prompt: 시스템 프롬프트 (기본 원칙 + 채널 프로필 + few-shot)
        video_title: 영상 제목
        video_desc: 영상 설명
        comments: [{"id": str, "author": str, "text": str}, ...]

    Returns:
        [{"index": int(1-based), "reply": str | None}, ...]
        실패 시 빈 리스트 (호출부가 다음 실행에서 재시도).
    """
    comment_list = "\n".join(
        f'{i + 1}. [{c["author"]}]: {c["text"]}' for i, c in enumerate(comments)
    )

    user_message = f"""[영상 제목]: {video_title}
[영상 설명]: {video_desc}

아래 댓글들 각각에 대한 답글을 JSON 배열로 반환하세요.
스팸이면 reply를 null로 설정하세요.

[댓글 목록]:
{comment_list}

반드시 JSON 배열로만 응답하세요:"""

    full_prompt = f"{system_prompt}\n\n---\n\n{user_message}"

    result = None
    try:
        env = os.environ.copy()
        # Claude Code 세션 안에서 하위 claude 호출이 막히지 않도록 제거 (유지 필수)
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            ["claude", "-p", "--model", "sonnet"],
            shell=(platform.system() == "Windows"),
            input=full_prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=CLAUDE_TIMEOUT,
            env=env,
        )

        if result.returncode != 0:
            logger.error("claude 호출 실패: %s", (result.stderr or "").strip()[:500])
            return []

        if not result.stdout:
            logger.error("claude 응답 없음 (stdout 비어있음)")
            return []

        logger.info("LLM 원본 응답: %s", result.stdout[:500])

        raw = _extract_json_array(result.stdout)
        replies = json.loads(raw)

        # LLM 응답 정규화: 배열 순서를 index로 사용 (키 이름이 불안정하므로)
        normalized = []
        for i, item in enumerate(replies):
            normalized.append({"index": i + 1, "reply": item.get("reply")})

        logger.info("LLM 정규화 결과: %d건", len(normalized))
        return normalized

    except FileNotFoundError:
        logger.error(
            "claude 명령을 찾을 수 없습니다. Claude Code가 설치되어 있는지 확인해주세요."
        )
        return []
    except subprocess.TimeoutExpired:
        logger.error("claude 응답 대기 시간 초과 (%d초)", CLAUDE_TIMEOUT)
        return []
    except json.JSONDecodeError as e:
        out = result.stdout[:500] if result is not None else ""
        logger.error("JSON 파싱 실패: %s\n원본: %s", e, out)
        return []
