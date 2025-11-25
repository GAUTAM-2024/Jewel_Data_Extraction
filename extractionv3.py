import argparse
import requests
from bs4 import BeautifulSoup

DEFAULT_URL = "https://ivanajewels.com/products/0-75-carat-lab-grown-diamond-studs"

def normalize(u: str) -> str:
    return "https:" + u if u.startswith("//") else u

def strip_to_jpg(u: str) -> str:
    i = u.lower().find(".jpg")
    return u[:i+4] if i != -1 else u

def parse_srcset(attr: str):
    variants = []
    if not attr:
        return variants
    # srcset format: url widthDescriptor (comma separated)
    for part in attr.split(','):
        part = part.strip()
        if not part:
            continue
        if ' ' in part:
            url_part, width_part = part.rsplit(' ', 1)
        else:
            url_part, width_part = part, ''
        url_part = url_part.strip()
        width = 0
        if width_part.endswith('w'):
            try:
                width = int(width_part[:-1])
            except ValueError:
                width = 0
        variants.append((normalize(url_part), width))
    return variants

def choose_best_variant(img_tag) -> str:
    srcset = img_tag.get('srcset') or img_tag.get('dt')  # some themes use custom attrs
    variants = parse_srcset(srcset)
    if variants:
        # pick highest width (fallback to non-zero width preference)
        variants.sort(key=lambda x: x[1], reverse=True)
        return variants[0][0]
    # fallback to src
    src = img_tag.get('src')
    if not src:
        return ''
    return normalize(src)

def extract_img_sources(img_tag, high_res: bool):
    # ordered fallbacks
    candidates = []
    if high_res:
        best = choose_best_variant(img_tag)
        if best:
            candidates.append(best)
    # raw attributes that may hold small or lazy srcs
    for attr in ["src", "data-src", "data-msrc", "d-src"]:
        val = img_tag.get(attr)
        if val:
            candidates.append(normalize(val))
    # de-duplicate preserve order
    seen_local = set()
    ordered = []
    for c in candidates:
        if c.startswith("data:"):
            continue
        if c not in seen_local:
            seen_local.add(c)
            ordered.append(c)
    return ordered

def get_product_slider_imgs(html: str, high_res: bool = True, include_links: bool = True):
    soup = BeautifulSoup(html, "html.parser")
    slider = soup.find(id="Product-Slider")
    if not slider:
        return []
    out = []
    seen = set()
    # IMG tags
    for img in slider.find_all("img"):
        for full in extract_img_sources(img, high_res):
            if not full:
                continue
            base = strip_to_jpg(full)
            if base not in seen:
                seen.add(base)
                out.append({"chosen_url": full, "base_jpg": base, "type": "img"})
    # Anchor hrefs (zoom links may reference full size) if requested
    if include_links:
        for a in slider.find_all("a"):
            href = a.get("href")
            if not href:
                continue
            href_norm = normalize(href)
            if href_norm.startswith("data:"):
                continue
            base = strip_to_jpg(href_norm)
            if base not in seen and base.lower().endswith('.jpg'):
                seen.add(base)
                out.append({"chosen_url": href_norm, "base_jpg": base, "type": "anchor"})
    return out

def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.text

def main():
    parser = argparse.ArgumentParser(description="Extract Product-Slider image URLs from a product page")
    parser.add_argument("--url", default=DEFAULT_URL, help="Product page URL")
    parser.add_argument("--lowres", action="store_true", help="Use raw src/lazy attrs instead of largest srcset variant")
    parser.add_argument("--no-links", action="store_true", help="Do not include anchor href image URLs")
    args = parser.parse_args()

    html = fetch_html(args.url)
    images = get_product_slider_imgs(html, high_res=not args.lowres, include_links=not args.no_links)
    print(f"Page: {args.url}")
    print(f"Found {len(images)} unique image entries in Product-Slider")
    for i, info in enumerate(images, 1):
        print(f"{i}. [{info['type']}] chosen={info['chosen_url']}  base={info['base_jpg']}")

if __name__ == "__main__":
    main()