"""
キーワード検索 → URL 取得、複数 URL の一括スクレイプ
"""

from __future__ import annotations

from datetime import datetime

from scraper.core import scrape_url, ScraperError, RobotsDisallowedError

# キーワード検索で取得する最大URL数
DEFAULT_MAX_SEARCH_RESULTS = 10
# 一括取得の最大URL数（UI用）
MAX_URLS = 30


def _extract_href(item: dict) -> str | None:
    """検索結果1件からURLを取得（パッケージ差を吸収）"""
    href = item.get("href") or item.get("link") or item.get("url")
    if isinstance(href, str) and href.startswith(("http://", "https://")):
        return href
    return None


def get_urls_from_keyword(keyword: str, max_results: int = DEFAULT_MAX_SEARCH_RESULTS) -> list[str]:
    """キーワードで検索し、結果のURLリストを返す（DuckDuckGo / ddgs）"""
    ddgs_class = None
    try:
        from ddgs import DDGS
        ddgs_class = DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
            ddgs_class = DDGS
        except ImportError:
            raise ScraperError(
                "キーワード検索には ddgs または duckduckgo-search のインストールが必要です。"
                " pip install ddgs を試してください。"
            )

    urls: list[str] = []
    try:
        with ddgs_class() as ddgs:
            # イテレータまたはリストの両方に対応
            raw = ddgs.text(keyword, max_results=max_results)
            if hasattr(raw, "__iter__") and not isinstance(raw, (str, bytes)):
                for r in raw:
                    if isinstance(r, dict):
                        h = _extract_href(r)
                        if h and h not in urls:
                            urls.append(h)
                    if len(urls) >= max_results:
                        break
    except Exception as e:
        raise ScraperError(f"検索に失敗しました: {type(e).__name__}: {e}")
    return urls[:max_results]


def scrape_urls(
    urls: list[str],
    *,
    delay_seconds: float = 1.5,
    check_robots: bool = True,
) -> list[dict]:
    """
    複数URLを順にスクレイプし、結果のリストを返す。
    各要素: { url, title, text, status, fetched_at }
    """
    results = []
    for url in urls:
        url = url.strip()
        if not url or not url.startswith(("http://", "https://")):
            continue
        fetched_at = datetime.now().isoformat()
        try:
            data = scrape_url(
                url,
                delay_seconds=delay_seconds,
                check_robots=check_robots,
                extract_text=True,
                extract_links=False,
            )
            results.append({
                "url": data["url"],
                "title": data["title"],
                "text": data["text"],
                "status": "ok",
                "fetched_at": fetched_at,
            })
        except RobotsDisallowedError:
            results.append({
                "url": url,
                "title": None,
                "text": None,
                "status": "robots_disallowed",
                "fetched_at": fetched_at,
            })
        except ScraperError as e:
            results.append({
                "url": url,
                "title": None,
                "text": None,
                "status": f"error: {e!s}"[:100],
                "fetched_at": fetched_at,
            })
        except Exception as e:
            results.append({
                "url": url,
                "title": None,
                "text": None,
                "status": f"error: {e!s}"[:100],
                "fetched_at": fetched_at,
            })
    return results


def run_job(
    *,
    urls: list[str] | None = None,
    keyword: str | None = None,
    max_results: int = DEFAULT_MAX_SEARCH_RESULTS,
    delay_seconds: float = 1.5,
    check_robots: bool = True,
) -> list[dict]:
    """
    URL またはキーワードから一括取得を実行する。
    - urls が渡されればそのままスクレイプ
    - keyword が渡されれば検索 → 得たURLをスクレイプ
    """
    if keyword:
        keyword = keyword.strip()
        if not keyword:
            raise ScraperError("キーワードを入力してください")
        urls = get_urls_from_keyword(keyword, max_results=max_results)
        if not urls:
            raise ScraperError("キーワードからURLを取得できませんでした")
    elif urls:
        urls = [u.strip() for u in urls if u.strip() and u.strip().startswith(("http://", "https://"))]
        if not urls:
            raise ScraperError("有効なURLを入力してください")
    else:
        raise ScraperError("URL またはキーワードを入力してください")

    if len(urls) > MAX_URLS:
        urls = urls[:MAX_URLS]
    return scrape_urls(urls, delay_seconds=delay_seconds, check_robots=check_robots)
