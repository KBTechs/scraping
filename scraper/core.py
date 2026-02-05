"""
robots.txt 確認とポライトな取得のコアロジック
"""

from __future__ import annotations

import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bs4 import BeautifulSoup


# デフォルトの User-Agent（ボットであることを明示）
DEFAULT_USER_AGENT = "PoliteScraper/1.0 (Python; +https://github.com)"
# リクエスト間の最低待機秒数（サイト負荷軽減）
DEFAULT_DELAY_SECONDS = 1.0
# タイムアウト
DEFAULT_TIMEOUT = 15


class ScraperError(Exception):
    """スクレイパー用の基底例外"""
    pass


class RobotsDisallowedError(ScraperError):
    """robots.txt で取得が禁止されている場合"""
    pass


def _robots_url(base_url: str) -> str:
    """対象URLから robots.txt のURLを返す"""
    parsed = urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"


def _session_with_retries(
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: int = DEFAULT_TIMEOUT,
) -> requests.Session:
    """リトライ付きの Session を返す（429/5xx 時に控えめにリトライ）"""
    session = requests.Session()
    session.headers["User-Agent"] = user_agent
    retries = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503],
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))
    return session


def can_fetch(
    url: str,
    user_agent: str = DEFAULT_USER_AGENT,
    session: requests.Session | None = None,
) -> bool:
    """
    指定URLが robots.txt で取得許可されているか確認する。
    robots.txt が存在しない、または取得できない場合は True を返す（許可とみなす）。
    """
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = _robots_url(base)

    use_session = session or _session_with_retries(user_agent=user_agent)
    try:
        resp = use_session.get(robots_url, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException:
        # 取得できない場合は許可とみなす（RFC の一般的な解釈）
        return True

    rp = RobotFileParser()
    rp.parse(resp.text.splitlines())
    return rp.can_fetch(user_agent, url)


def fetch_page(
    url: str,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    timeout: int = DEFAULT_TIMEOUT,
    check_robots: bool = True,
    session: requests.Session | None = None,
) -> requests.Response:
    """
    指定URLのページを1回だけ取得する。
    - check_robots=True のときは robots.txt を確認し、禁止なら RobotsDisallowedError
    - 取得前に delay_seconds だけ待機（同一セッションで連続呼び出しを想定）
    """
    if check_robots:
        if not can_fetch(url, user_agent=user_agent, session=session):
            raise RobotsDisallowedError(
                f"robots.txt により取得が禁止されています: {url}"
            )
    time.sleep(delay_seconds)

    use_session = session or _session_with_retries(
        user_agent=user_agent, timeout=timeout
    )
    use_session.headers["User-Agent"] = user_agent
    resp = use_session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp


def scrape_url(
    url: str,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    timeout: int = DEFAULT_TIMEOUT,
    check_robots: bool = True,
    extract_text: bool = True,
    extract_links: bool = False,
) -> dict:
    """
    指定URLから情報を取得する。
    - robots.txt を確認し、許可されている場合のみ取得
    - 戻り値: {
        "url": str,
        "status_code": int,
        "title": str | None,
        "text": str | None,   # extract_text=True の場合
        "links": list[str] | None,  # extract_links=True の場合
        "soup": BeautifulSoup | None,  # 生のパース結果を使いたい場合
      }
    """
    resp = fetch_page(
        url,
        user_agent=user_agent,
        delay_seconds=delay_seconds,
        timeout=timeout,
        check_robots=check_robots,
    )

    result = {
        "url": url,
        "status_code": resp.status_code,
        "title": None,
        "text": None,
        "links": None,
        "soup": None,
    }

    content_type = resp.headers.get("Content-Type", "")
    if "text/html" not in content_type.lower():
        result["text"] = resp.text[:2000] if extract_text else None
        return result

    soup = BeautifulSoup(resp.content, "html.parser")

    if soup.title:
        result["title"] = soup.title.get_text(strip=True)

    if extract_text:
        for tag in soup(["script", "style"]):
            tag.decompose()
        result["text"] = soup.get_text(separator="\n", strip=True)

    if extract_links:
        base = urljoin(url, "/")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href and not href.startswith("#"):
                full = urljoin(base, href)
                if full not in links:
                    links.append(full)
        result["links"] = links

    result["soup"] = soup
    return result
