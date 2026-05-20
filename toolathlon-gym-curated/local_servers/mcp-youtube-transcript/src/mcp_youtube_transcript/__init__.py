#  __init__.py
#
#  Copyright (c) 2025 Junpei Kawamoto
#
#  This software is released under the MIT License.
#
#  http://opensource.org/licenses/mit-license.php
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from functools import partial
from itertools import islice
from typing import AsyncIterator, Final, Tuple
from urllib.parse import parse_qs, urlparse

import humanize
import requests
import yt_dlp
from mcp import ServerSession
from mcp.server import FastMCP
from mcp.server.fastmcp import Context
from pydantic import AwareDatetime, BaseModel, Field
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._transcripts import FetchedTranscriptSnippet
from youtube_transcript_api.proxies import (
    GenericProxyConfig,
    ProxyConfig,
    WebshareProxyConfig,
)
from yt_dlp.extractor.youtube import YoutubeIE


def _parse_video_id(url: str) -> str:
    parsed_url = urlparse(url)
    if parsed_url.hostname == "youtu.be":
        return parsed_url.path.lstrip("/")
    q = parse_qs(parsed_url.query).get("v")
    if q:
        return q[0]
    return url


def _parse_time_info(
    upload_date: int | str,
    timestamp: int,
    duration: int,
) -> tuple[datetime, str]:
    """Parse legacy date/time payloads into API-ready values."""
    date_part = datetime.strptime(str(upload_date), "%Y%m%d")
    time_digits = str(timestamp).zfill(10)
    hour = int(time_digits[0:2])
    minute = int(time_digits[2:4])
    second = int(time_digits[4:6])
    millisecond = int(time_digits[6:9])
    parsed_upload_date = datetime(
        date_part.year,
        date_part.month,
        date_part.day,
        hour,
        minute,
        second,
        millisecond * 1000,
        timezone.utc,
    )
    parsed_duration = humanize.naturaldelta(timedelta(seconds=duration))
    return parsed_upload_date, parsed_duration


def _build_proxy_config(
    webshare_proxy_username: str | None,
    webshare_proxy_password: str | None,
    http_proxy: str | None,
    https_proxy: str | None,
) -> ProxyConfig | None:
    """Return a youtube_transcript_api ProxyConfig, or None if no proxy."""
    if webshare_proxy_username and webshare_proxy_password:
        return WebshareProxyConfig(webshare_proxy_username, webshare_proxy_password)
    if http_proxy or https_proxy:
        return GenericProxyConfig(http_proxy, https_proxy)
    return None


@dataclass(frozen=True)
class AppContext:
    http_client: requests.Session = field(default_factory=requests.Session)
    ytt_api: YouTubeTranscriptApi = field(default_factory=YouTubeTranscriptApi)
    dlp: yt_dlp.YoutubeDL = field(default_factory=lambda: yt_dlp.YoutubeDL({"quiet": True}))


@asynccontextmanager
async def _app_lifespan(
    _server: FastMCP,
    proxy_config: ProxyConfig | None = None,
    ydl_proxy: str | None = None,
) -> AsyncIterator[AppContext]:
    http_client = requests.Session()
    if proxy_config is not None:
        http_client.proxies.update(proxy_config.to_requests_dict())

    ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config, http_client=http_client)

    ydl_opts: dict = {"quiet": True}
    if ydl_proxy:
        ydl_opts["proxy"] = ydl_proxy
    dlp = yt_dlp.YoutubeDL(ydl_opts)

    yield AppContext(http_client=http_client, ytt_api=ytt_api, dlp=dlp)

    dlp.close()
    http_client.close()


class Transcript(BaseModel):
    """Transcript of a YouTube video."""

    title: str = Field(description="Title of the video")
    transcript: str = Field(description="Transcript of the video")
    next_cursor: str | None = Field(
        description="Cursor to retrieve the next page of the transcript", default=None
    )


class TranscriptSnippet(BaseModel):
    """Transcript snippet of a YouTube video."""

    text: str = Field(description="Text of the transcript snippet")
    start: float = Field(
        description="The timestamp at which this transcript snippet appears on screen in seconds."
    )
    duration: float = Field(description="The duration of how long the snippet in seconds.")

    @classmethod
    def from_fetched_transcript_snippet(cls, snippet: FetchedTranscriptSnippet) -> "TranscriptSnippet":
        """Create a TranscriptSnippet from a FetchedTranscriptSnippet."""
        return cls(
            text=snippet.text,
            start=snippet.start,
            duration=snippet.duration,
        )

    def __len__(self) -> int:
        return len(self.model_dump_json())


class TimedTranscript(BaseModel):
    """Transcript of a YouTube video with timestamps."""

    title: str = Field(description="Title of the video")
    snippets: list[TranscriptSnippet] = Field(description="Transcript snippets of the video")
    next_cursor: str | None = Field(
        description="Cursor to retrieve the next page of the transcript", default=None
    )


class VideoInfo(BaseModel):
    """Video information."""

    title: str = Field(description="Title of the video")
    description: str = Field(description="Description of the video")
    uploader: str = Field(description="Uploader of the video")
    upload_date: AwareDatetime = Field(description="Upload date of the video")
    duration: str = Field(description="Duration of the video")


def _ydl_proxy_from_config(proxy_config: ProxyConfig | None) -> str | None:
    """Extract the most useful single proxy URL for yt_dlp from a ProxyConfig."""
    if proxy_config is None:
        return None
    d = proxy_config.to_requests_dict()
    # Prefer https proxy, fall back to http
    return d.get("https") or d.get("http")


def server(
    response_limit: int | None = None,
    webshare_proxy_username: str | None = None,
    webshare_proxy_password: str | None = None,
    http_proxy: str | None = None,
    https_proxy: str | None = None,
) -> FastMCP:
    """Initializes the MCP server."""

    proxy_config = _build_proxy_config(
        webshare_proxy_username, webshare_proxy_password, http_proxy, https_proxy
    )
    ydl_proxy = _ydl_proxy_from_config(proxy_config)

    mcp = FastMCP(
        "Youtube Transcript",
        lifespan=partial(_app_lifespan, proxy_config=proxy_config, ydl_proxy=ydl_proxy),
    )

    @mcp.tool()
    async def get_transcript(
        ctx: Context[ServerSession, AppContext],
        url: str = Field(description="The URL or video ID of the YouTube video"),
        lang: str = Field(description="The preferred language for the transcript", default="en"),
        next_cursor: str | None = Field(
            description="Cursor to retrieve the next page of the transcript", default=None
        ),
    ) -> Transcript:
        """Retrieves the transcript of a YouTube video."""
        video_id = _parse_video_id(url)
        app_ctx: AppContext = ctx.request_context.lifespan_context
        try:
            fetched = app_ctx.ytt_api.fetch(video_id, [lang])
        except Exception:
            fetched = app_ctx.ytt_api.fetch(video_id)
        title = video_id
        try:
            app_ctx.dlp.add_info_extractor(YoutubeIE())
            info = app_ctx.dlp.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )
            title = info.get("title", video_id)
        except Exception:
            pass
        texts = (s.text for s in fetched)

        if response_limit is None or response_limit <= 0:
            return Transcript(title=title, transcript="\n".join(texts))

        res = ""
        cursor = None
        for i, line in islice(enumerate(texts), int(next_cursor or 0), None):
            if len(res) + len(line) + 1 > response_limit:
                cursor = str(i)
                break
            res += f"{line}\n"

        return Transcript(title=title, transcript=res.rstrip("\n"), next_cursor=cursor)

    @mcp.tool()
    async def get_timed_transcript(
        ctx: Context[ServerSession, AppContext],
        url: str = Field(description="The URL or video ID of the YouTube video"),
        lang: str = Field(description="The preferred language for the transcript", default="en"),
        next_cursor: str | None = Field(
            description="Cursor to retrieve the next page of the transcript", default=None
        ),
    ) -> TimedTranscript:
        """Retrieves the transcript of a YouTube video with timestamps."""
        video_id = _parse_video_id(url)
        app_ctx: AppContext = ctx.request_context.lifespan_context
        try:
            fetched = app_ctx.ytt_api.fetch(video_id, [lang])
        except Exception:
            fetched = app_ctx.ytt_api.fetch(video_id)
        title = video_id
        try:
            app_ctx.dlp.add_info_extractor(YoutubeIE())
            info = app_ctx.dlp.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )
            title = info.get("title", video_id)
        except Exception:
            pass
        snippet_objs = [TranscriptSnippet.from_fetched_transcript_snippet(s) for s in fetched]

        if response_limit is None or response_limit <= 0:
            return TimedTranscript(title=title, snippets=snippet_objs)

        res = []
        size = len(title) + 1
        cursor = None
        for i, snippet in islice(enumerate(snippet_objs), int(next_cursor or 0), None):
            if size + len(snippet) + 1 > response_limit:
                cursor = str(i)
                break
            res.append(snippet)
            size += len(snippet) + 1

        return TimedTranscript(title=title, snippets=res, next_cursor=cursor)

    @mcp.tool()
    def get_video_info(
        ctx: Context[ServerSession, AppContext],
        url: str = Field(description="The URL or video ID of the YouTube video"),
    ) -> VideoInfo:
        """Retrieves the video information."""
        video_id = _parse_video_id(url)
        app_ctx: AppContext = ctx.request_context.lifespan_context
        app_ctx.dlp.add_info_extractor(YoutubeIE())
        info = app_ctx.dlp.extract_info(
            f"https://www.youtube.com/watch?v={video_id}", download=False
        )
        upload_date, duration = _parse_time_info(
            info["upload_date"], info["timestamp"], info["duration"]
        )
        return VideoInfo(
            title=info["title"],
            description=info.get("description") or "",
            uploader=info.get("uploader") or "",
            upload_date=upload_date,
            duration=duration,
        )

    return mcp


__all__: Final = [
    "server",
    "AppContext",
    "Transcript",
    "TimedTranscript",
    "TranscriptSnippet",
    "VideoInfo",
    "_parse_time_info",
]
