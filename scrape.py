#!/usr/bin/env python3
"""
指定URLから情報を取得するCLI。
robots.txt で許可されている場合のみ取得し、サイトに負荷をかけないように配慮します。

使用例:
  python scrape.py https://example.com
  python scrape.py https://example.com --no-robots-check
  python scrape.py https://example.com --links --delay 2
"""

import argparse
import json
import sys

from scraper import (
    can_fetch,
    scrape_url,
    RobotsDisallowedError,
    ScraperError,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="指定URLから情報を取得（robots.txt 尊重・ポライト取得）"
    )
    parser.add_argument(
        "url",
        help="取得するページのURL",
    )
    parser.add_argument(
        "--no-robots-check",
        action="store_true",
        help="robots.txt を確認しない（自己責任で使用）",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        metavar="SEC",
        help="リクエスト前の待機秒数（デフォルト: 1.0）",
    )
    parser.add_argument(
        "--links",
        action="store_true",
        help="ページ内のリンク一覧も抽出する",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="robots.txt の可否のみ表示し、取得は行わない",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="結果をJSONで出力（text は先頭2000文字に制限）",
    )
    args = parser.parse_args()

    url = args.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        if args.check_only:
            allowed = can_fetch(url)
            print("OK: 取得可能" if allowed else "NG: robots.txt により取得禁止")
            return 0 if allowed else 1

        data = scrape_url(
            url,
            check_robots=not args.no_robots_check,
            delay_seconds=args.delay,
            extract_text=True,
            extract_links=args.links,
        )
    except RobotsDisallowedError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    except ScraperError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    if args.json:
        out = {
            "url": data["url"],
            "status_code": data["status_code"],
            "title": data["title"],
            "text": (data["text"] or "")[:2000],
            "links": data["links"],
        }
        if data["links"] is None:
            del out["links"]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    print(f"URL: {data['url']}")
    print(f"ステータス: {data['status_code']}")
    print(f"タイトル: {data['title'] or '(なし)'}")
    if data["text"]:
        preview = data["text"][:500].replace("\n", " ")
        print(f"本文（先頭500文字）: {preview}...")
    if data["links"]:
        print(f"リンク数: {len(data['links'])}")
        for link in data["links"][:10]:
            print(f"  - {link}")
        if len(data["links"]) > 10:
            print(f"  ... 他 {len(data['links']) - 10} 件")

    return 0


if __name__ == "__main__":
    sys.exit(main())
