# scraping

指定URLから情報を取得する Python スクレイピングツール。  
**robots.txt を確認し、取得が許可されている場合のみ**アクセスします。サイトに負荷をかけないよう、待機時間・User-Agent・リトライを考慮しています。

## セットアップ

```bash
cd /path/to/scraping
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 使い方

### 指定URLから情報を取得

```bash
python scrape.py https://example.com
```

### オプション

| オプション | 説明 |
|-----------|------|
| `--no-robots-check` | robots.txt を確認しない（自己責任） |
| `--delay SEC` | リクエスト前の待機秒数（デフォルト: 1.0） |
| `--links` | ページ内のリンク一覧も抽出 |
| `--check-only` | robots.txt の可否のみ表示し、取得は行わない |
| `--json` | 結果をJSONで出力 |

例:

```bash
# robots.txt のみ確認
python scrape.py https://example.com --check-only

# リンクも取得し、2秒待機
python scrape.py https://example.com --links --delay 2

# 結果をJSONで
python scrape.py https://example.com --json
```

### コードから使う

```python
from scraper import scrape_url, can_fetch, RobotsDisallowedError

# 取得可否だけ確認
if can_fetch("https://example.com/page"):
    print("取得可能")

# ページ取得（テキスト・リンク・BeautifulSoup）
try:
    data = scrape_url(
        "https://example.com",
        delay_seconds=1.0,
        extract_text=True,
        extract_links=True,
    )
    print(data["title"], data["text"][:200])
except RobotsDisallowedError:
    print("robots.txt で禁止されています")
```

## フレームワークについて（Playwright との比較）

今回の実装は **Requests + BeautifulSoup** です。

| 方式 | 向いている場面 | 特徴 |
|------|----------------|------|
| **Requests + BeautifulSoup**（本ツール） | 静的HTML、API的なページ、軽いスクレイピング | 軽量・高速・依存が少ない。JavaScript で描画される部分は取れない。 |
| **Playwright** | SPA、ログイン必須、JSで内容が変わるページ | ブラウザを動かすので確実だが重い。ヘッドレスで「表示後のHTML」が取れる。 |
| **Scrapy** | 大量のURLを回るクロール、パイプラインで保存 | フレームワークとして robots.txt・レート制限・キューが組み込み。単一URL取得には過剰になりがち。 |

**おすすめの選び方**

- **まずはこのツール（Requests + BeautifulSoup）**で試し、取得したい情報が HTML に最初から含まれていればそのままで十分です。
- ページを開いたあと JavaScript でコンテンツが描画されるサイト（例: React/Vue の SPA）では、**Playwright** を検討してください。必要なら Playwright 用のラッパーを追加することもできます。

## サイトに負担をかけないための配慮

- **robots.txt**: 取得許可のパスのみアクセス（`can_fetch` / デフォルトで `check_robots=True`）
- **待機時間**: リクエスト前に `delay_seconds`（デフォルト 1 秒）を挿入
- **User-Agent**: ボットであることを明示（`PoliteScraper/1.0`）
- **リトライ**: 429 / 5xx 時に控えめにリトライし、`Retry-After` を尊重
- **タイムアウト**: デフォルト 15 秒で打ち切り

## ライセンス

MIT
