import re
import sys
import urllib.error
import urllib.request


def fetch(url: str, timeout: int = 15) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "analytics-portal-smoke/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8", errors="replace")
        return int(getattr(r, "status", 200)), body


def extract_block(html: str, block_id: str) -> str:
    # Best-effort extraction: start at the element with id="..." and take a large slice.
    m = re.search(rf'id="{re.escape(block_id)}"', html)
    if not m:
        return ""
    return html[m.start() : m.start() + 250_000]


def main() -> int:
    dataset_id = sys.argv[1] if len(sys.argv) > 1 else "26"
    url = f"http://127.0.0.1:8000/dataset/{dataset_id}/stats/?tab=products"

    try:
        status, html = fetch(url)
    except (urllib.error.URLError, TimeoutError) as e:
        print("ERR_FETCH", type(e).__name__, str(e))
        return 2

    print("url", url)
    print("status", status, "len", len(html))

    # Basic markers
    markers = {
        "has_products_tab": 'id="products"' in html,
        "has_products_month": 'id="products-month-period"' in html,
        "has_products_quarter": 'id="products-quarter-period"' in html,
        "has_products_fiscal": 'id="products-fiscal-period"' in html,
    }
    for k, v in markers.items():
        print(k, v)

    # Plotly markers
    plotly_cdn_refs = html.count("cdn.plot.ly") + html.count("plotly-latest.min.js")
    plotly_graph_divs = html.count("plotly-graph-div")
    print("plotly_cdn_refs", plotly_cdn_refs)
    print("plotly_graph_divs", plotly_graph_divs)

    # Per-pill quick checks
    pills = [
        "products-month-period",
        "products-quarter-period",
        "products-fiscal-period",
    ]

    for pill in pills:
        block = extract_block(html, pill)
        print("\n--", pill)
        print("block_len", len(block))
        print("has_table", "<table" in block)
        print("has_plotly", "plotly-graph-div" in block)
        print("has_warning", "Analyse des familles indisponible" in block)
        print("has_insufficient", "Pas de données suffisantes" in block)

    # Check for server-side errors leaked
    print("\ncontains_template_traceback", "Traceback (most recent call last)" in html)
    print("contains_internal_server_error", "Server Error (500)" in html)

    # Non-fatal exit code policy: fail only if missing all plotly or core tabs
    if status >= 500:
        return 3
    if not markers["has_products_tab"]:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
