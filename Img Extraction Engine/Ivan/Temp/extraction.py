import re
import os
import argparse
import datetime
import requests
import pandas as pd  # Excel support (future use)
from bs4 import BeautifulSoup

DEFAULT_URL = "https://ivanajewels.com/products/0-75-carat-lab-grown-diamond-studs"
OUTPUT_LOG = "output_logging.txt"

def normalize_url(raw: str) -> str:
    if raw.startswith("//"):
        return "https:" + raw
    return raw

def base_jpg(url: str) -> str:
    # Return substring up to and including .jpg (drop query string or fragments)
    m = re.search(r"\.jpg", url)
    if not m:
        return url
    end = m.end()
    return url[:end]

def parse_width(url: str, descriptor: str | None) -> int:
    # Priority: width descriptor (e.g. 1220w) if provided, else query param &width=, else 0
    if descriptor and descriptor.endswith("w") and descriptor[:-1].isdigit():
        return int(descriptor[:-1])
    q = re.search(r"[?&]width=(\d+)", url)
    if q:
        return int(q.group(1))
    return 0

def extract_max_image_bases(soup: BeautifulSoup) -> list[str]:
    product_slider = soup.find(id="Product-Slider")
    if not product_slider:
        return []
    groups: dict[str, tuple[int, str]] = {}  # base -> (max_width, chosen_full_url)
    for img in product_slider.find_all("img"):
        # Collect src
        src = img.get("src")
        if src:
            src = normalize_url(src)
            w = parse_width(src, None)
            b = base_jpg(src)
            current = groups.get(b)
            if current is None or w > current[0]:
                groups[b] = (w, src)
        # Collect srcset variants
        srcset = img.get("srcset")
        if srcset:
            for part in srcset.split(","):
                part = part.strip()
                if not part:
                    continue
                pieces = part.split()
                candidate_url = normalize_url(pieces[0])
                descriptor = pieces[1] if len(pieces) > 1 else None
                w = parse_width(candidate_url, descriptor)
                b = base_jpg(candidate_url)
                current = groups.get(b)
                if current is None or w > current[0]:
                    groups[b] = (w, candidate_url)
    # Return only base .jpg paths for max width variant per image group
    return list(groups.keys())

def extract_max_full_urls(soup: BeautifulSoup) -> list[str]:
    """Return the full chosen URL (including query) for max-width variant of each image group."""
    product_slider = soup.find(id="Product-Slider")
    if not product_slider:
        return []
    groups: dict[str, tuple[int, str]] = {}
    for img in product_slider.find_all("img"):
        src = img.get("src")
        if src:
            src = normalize_url(src)
            w = parse_width(src, None)
            b = base_jpg(src)
            current = groups.get(b)
            if current is None or w > current[0]:
                groups[b] = (w, src)
        srcset = img.get("srcset")
        if srcset:
            for part in srcset.split(","):
                part = part.strip()
                if not part:
                    continue
                pieces = part.split()
                candidate_url = normalize_url(pieces[0])
                descriptor = pieces[1] if len(pieces) > 1 else None
                w = parse_width(candidate_url, descriptor)
                b = base_jpg(candidate_url)
                current = groups.get(b)
                if current is None or w > current[0]:
                    groups[b] = (w, candidate_url)
    return [v[1] for v in groups.values()]

def extract_all_image_urls(soup: BeautifulSoup) -> list[str]:
    """Return one base .jpg per <img> tag (max width variant if srcset exists)."""
    product_slider = soup.find(id="Product-Slider")
    if not product_slider:
        return []
    results: list[str] = []
    for img in product_slider.find_all("img"):
        chosen_full = None
        max_w = -1
        srcset = img.get("srcset")
        if srcset:
            for part in srcset.split(","):
                part = part.strip()
                if not part:
                    continue
                pieces = part.split()
                candidate_url = normalize_url(pieces[0])
                descriptor = pieces[1] if len(pieces) > 1 else None
                w = parse_width(candidate_url, descriptor)
                if w > max_w:
                    max_w = w
                    chosen_full = candidate_url
        if chosen_full is None:  # fallback to src
            src = img.get("src")
            if src:
                chosen_full = normalize_url(src)
        if chosen_full:
            results.append(base_jpg(chosen_full))
    return results

def write_log_line(line: str) -> None:
    with open(OUTPUT_LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")

def log_event(stage: str, page_url: str, image_base: str | None = None, image_full: str | None = None,
              status: str | None = None, note: str | None = None) -> None:
    ts = datetime.datetime.now(datetime.UTC).isoformat()
    parts = {
        "timestamp": ts,
        "stage": stage,
        "page_url": page_url,
        "image_base": image_base or "",
        "image_full": image_full or "",
        "status": status or "",
        "note": note or ""
    }
    # Pipe-delimited for easy Excel import later
    line = "|".join(parts.values())
    write_log_line(line)

def process_html(html: str, page_url: str, download: bool, download_dir: str, debug: bool) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    slider = soup.find(id="Product-Slider")
    if not slider:
        print("WARNING: Product-Slider element not found.")
        log_event("slider_missing", page_url, status="no_slider", note="Product-Slider element not found")
        return []
    if debug:
        print("Product-Slider found; extracting images...")
    log_event("slider_found", page_url, status="ok")
    # Collect unique base .jpg from each img (largest variant by srcset if present)
    unique_bases: list[str] = []
    seen = set()
    base_to_full: dict[str, str] = {}
    for img in slider.find_all("img"):
        chosen_full = None
        max_w = -1
        srcset = img.get("srcset")
        if srcset:
            for part in srcset.split(","):
                part = part.strip()
                if not part:
                    continue
                pieces = part.split()
                candidate_url = normalize_url(pieces[0])
                descriptor = pieces[1] if len(pieces) > 1 else None
                w = parse_width(candidate_url, descriptor)
                if w > max_w:
                    max_w = w
                    chosen_full = candidate_url
        if chosen_full is None:
            src = img.get("src")
            if src:
                chosen_full = normalize_url(src)
        if not chosen_full:
            continue
        base = base_jpg(chosen_full)
        if base not in seen:
            seen.add(base)
            unique_bases.append(base)
            base_to_full[base] = chosen_full  # store original (may include query params)
            log_event("image_selected", page_url, image_base=base, image_full=chosen_full, status="selected", note=f"width={max_w if max_w!=-1 else 'src'}")
        if debug:
            print(f"IMG chosen: full={chosen_full} base={base} width={max_w if max_w!=-1 else 'src'}")

    print("Base .jpg URLs:")
    for i, b in enumerate(unique_bases, start=1):
        print(f"{i}. {b}")
    log_event("extraction_complete", page_url, status="count", note=f"images={len(unique_bases)}")
    if download:
        os.makedirs(download_dir, exist_ok=True)
        print(f"Downloading {len(unique_bases)} images to {os.path.abspath(download_dir)} (overwrite enabled)...")
        for i, b in enumerate(unique_bases, start=1):
            # Use base URL without query; ensure protocol
            base_url = b if b.startswith("http") else ("https:" + b if b.startswith("//") else b)
            original_full = base_to_full.get(b, base_url)
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            try:
                resp = requests.get(base_url, timeout=30, headers=headers)
                status = resp.status_code
                ctype = resp.headers.get("Content-Type", "")
                if status == 404 or not ctype.startswith("image") or len(resp.content) < 500:
                    if debug:
                        print(f"Base URL fallback triggered for {base_url} (status={status}, type={ctype}, size={len(resp.content)}) -> trying original with query")
                    # Retry with original full URL including query params
                    alt_url = original_full if original_full != base_url else None
                    if alt_url:
                        resp = requests.get(alt_url if alt_url.startswith("http") else ("https:" + alt_url if alt_url.startswith("//") else alt_url), timeout=30, headers=headers)
                        status = resp.status_code
                        ctype = resp.headers.get("Content-Type", "")
                resp.raise_for_status()
                if not ctype.startswith("image"):
                    raise ValueError(f"Non-image content-type {ctype}")
                filename = f"{i}_{b.rsplit('/',1)[-1]}"
                path = os.path.join(download_dir, filename)
                with open(path, "wb") as fh:
                    fh.write(resp.content)
                size = os.path.getsize(path)
                print(f"Saved {filename} status={status} type={ctype} size={size}")
                log_event("download_success", page_url, image_base=b, image_full=base_url, status=str(status), note=f"size={size}")
            except Exception as e:
                print(f"Failed {base_url}: {e}")
                log_event("download_failure", page_url, image_base=b, image_full=base_url, status="error", note=str(e))
        # Post-download verification
        written = sorted(os.listdir(download_dir))
        log_event("download_directory_scan", page_url, status="files", note=",".join(written))
    return unique_bases

def main():
    parser = argparse.ArgumentParser(description="Extract product slider images.")
    parser.add_argument("--file", "-f", help="Path to local Product_Slider.html snapshot instead of live fetch.")
    parser.add_argument("--live", action="store_true", help="Force live fetch even if --file given.")
    parser.add_argument("--download", action="store_true", help="Download max-width images to ./downloaded_images.")
    parser.add_argument("--download-dir", default="downloaded_images", help="Target directory for downloads.")
    parser.add_argument("--debug", action="store_true", help="Verbose debug output.")
    parser.add_argument("--url", help="Single product page URL to process (overrides default).")
    parser.add_argument("--excel", help="Excel (.xlsx/.csv) file containing product URLs.")
    parser.add_argument("--excel-column", default="url", help="Column name with product URLs.")
    args = parser.parse_args()

    # Write log header if new file
    if not os.path.exists(OUTPUT_LOG):
        write_log_line("timestamp|stage|page_url|image_base|image_full|status|note")

    targets: list[str] = []
    if args.excel:
        # Load URLs from Excel/CSV
        try:
            if args.excel.lower().endswith(".csv"):
                df = pd.read_csv(args.excel)
            else:
                df = pd.read_excel(args.excel)
            if args.excel_column not in df.columns:
                print(f"Column {args.excel_column} not found in Excel. Available: {list(df.columns)}")
                return
            targets = [str(u).strip() for u in df[args.excel_column] if str(u).strip()]
        except Exception as e:
            print(f"Failed to read Excel file: {e}")
            return
    elif args.url:
        targets = [args.url]
    elif args.file and not args.live and os.path.isfile(args.file):
        # Local file snapshot only; treat as single HTML source, not URL fetch
        with open(args.file, "r", encoding="utf-8") as fh:
            html = fh.read()
        process_html(html, args.file, args.download, args.download_dir, args.debug)
        return
    else:
        targets = [DEFAULT_URL]

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for idx, url in enumerate(targets, start=1):
        print(f"\n[{idx}/{len(targets)}] Fetching: {url}")
        try:
            resp = requests.get(url, timeout=30, headers=headers)
            resp.raise_for_status()
            process_html(resp.text, url, args.download, args.download_dir, args.debug)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            log_event("fetch_failure", url, status="error", note=str(e))

if __name__ == "__main__":
    main()