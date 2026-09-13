"""YouTube API 래퍼: 댓글 조회, 답글 게시, 기존 답글(톤) 수집.

모든 경로는 호출부(main.py)가 프로젝트 루트 기준 절대경로로 넘긴다.
"""

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def get_youtube_service(token_path: Path):
    """인증된 YouTube API 서비스 객체 반환. 토큰 만료 시 자동 갱신."""
    creds = Credentials.from_authorized_user_file(str(token_path))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def get_my_channel(service) -> dict | None:
    """인증된 계정의 채널 정보. {"id": str, "title": str} 또는 None."""
    response = service.channels().list(part="id,snippet", mine=True).execute()
    items = response.get("items", [])
    if not items:
        return None
    return {"id": items[0]["id"], "title": items[0]["snippet"]["title"]}


def fetch_recent_comments(service, channel_id: str, max_results: int = 30) -> list:
    """채널의 최근 댓글(최상위)을 최신순으로 가져오기.

    Returns:
        [{"id", "video_id", "author", "author_channel_id", "text"}, ...]
    """
    comments = []
    page_token = None

    while len(comments) < max_results:
        response = service.commentThreads().list(
            allThreadsRelatedToChannelId=channel_id,
            part="snippet",
            maxResults=min(100, max_results - len(comments)),
            order="time",
            pageToken=page_token,
        ).execute()

        for item in response.get("items", []):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            comments.append({
                "id": item["id"],
                "video_id": snippet["videoId"],
                "author": snippet["authorDisplayName"],
                "author_channel_id": snippet.get("authorChannelId", {}).get("value", ""),
                "text": snippet["textOriginal"],
            })

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return comments


def get_video_info(service, video_id: str) -> dict:
    """영상 제목과 설명(500자) 가져오기."""
    response = service.videos().list(part="snippet", id=video_id).execute()
    if not response["items"]:
        return {"title": "", "description": ""}
    snippet = response["items"][0]["snippet"]
    return {
        "title": snippet["title"],
        "description": snippet["description"][:500],
    }


def get_video_comment_count(service, video_id: str) -> int:
    """영상의 총 댓글 수 (commentCount 캐시 비교용 — API 절약 안전장치)."""
    response = service.videos().list(part="statistics", id=video_id).execute()
    if not response["items"]:
        return 0
    return int(response["items"][0]["statistics"].get("commentCount", 0))


def post_reply(service, parent_comment_id: str, text: str) -> str:
    """댓글에 답글 게시. 생성된 답글 ID 반환."""
    response = service.comments().insert(
        part="snippet",
        body={
            "snippet": {
                "parentId": parent_comment_id,
                "textOriginal": text,
            }
        },
    ).execute()
    return response["id"]


def collect_tone_examples(service, channel_id: str, max_videos: int = 10, limit: int = 20) -> list:
    """채널 소유자가 과거에 단 답글을 수집해 few-shot(말투 학습) 예시 생성.

    "내가 예전에 단 답글을 AI가 학습해서 내 말투로 답한다"의 핵심 자산.

    Returns:
        [{"comment": str, "reply": str}, ...]
    """
    search_response = service.search().list(
        channelId=channel_id,
        part="id",
        order="date",
        maxResults=max_videos,
        type="video",
    ).execute()

    video_ids = [item["id"]["videoId"] for item in search_response.get("items", [])]
    examples = []

    for video_id in video_ids:
        try:
            threads_response = service.commentThreads().list(
                videoId=video_id,
                part="snippet,replies",
                maxResults=100,
            ).execute()
        except Exception:
            continue

        for thread in threads_response.get("items", []):
            replies = thread.get("replies", {}).get("comments", [])
            for reply in replies:
                reply_snippet = reply["snippet"]
                # 채널 소유자의 답글만 수집
                if reply_snippet.get("authorChannelId", {}).get("value") == channel_id:
                    parent_text = thread["snippet"]["topLevelComment"]["snippet"]["textOriginal"]
                    examples.append({
                        "comment": parent_text,
                        "reply": reply_snippet["textOriginal"],
                    })

        if len(examples) >= limit:
            break

    return examples[:limit]


def save_tone_examples(examples: list, path: Path):
    path.write_text(json.dumps(examples, ensure_ascii=False, indent=2), encoding="utf-8")


def load_tone_examples(path: Path) -> list | None:
    """파일 없으면 None, 있으면 (빈 리스트 포함) 그대로 반환."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
