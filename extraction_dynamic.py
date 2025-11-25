import argparse
import requests
from bs4 import BeautifulSoup

def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.text

def normalize(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    return url

def strip_to_jpg(url: str) -> str:
    """Return substring up to and including .jpg (case-insensitive). If .jpg not found, return original."""
    idx = url.lower().find('.jpg')
    return url[:idx+4] if idx != -1 else url

def extract_image_srcs(html: str, container_tag: str, container_id: str, include_both: bool = False) -> list[str]:
    """Return unique image URLs inside the container.

    Priority rules:
    - If d-src exists and is not a data URI, prefer it over src placeholder.
    - If include_both=True and both src and d-src are real (non data:) and different, keep both.
    - Skip any data: (base64) placeholders.
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(container_tag, id=container_id)
    if not container:
        return []
    collected = []
    seen = set()
    for img in container.find_all("img"):
        raw_src = img.get("src")
        d_src = img.get("d-src")

        candidates = []
        # Prefer d-src if present
        if d_src and not d_src.startswith("data:"):
            candidates.append(d_src)
            # Optionally keep src if requested and valid and different
            if include_both and raw_src and not raw_src.startswith("data:") and raw_src != d_src:
                candidates.append(raw_src)
        else:
            # Fallback to src if usable
            if raw_src and not raw_src.startswith("data:"):
                candidates.append(raw_src)

        for c in candidates:
            norm = normalize(c)
            base = strip_to_jpg(norm)
            if base not in seen:
                seen.add(base)
                collected.append(base)
    return collected

def find_container(html: str, container_tag: str, container_id: str):
    soup = BeautifulSoup(html, "html.parser")
    return soup.find(container_tag, id=container_id)

def main():
    parser = argparse.ArgumentParser(description="Extract img src values from a custom slider element")
    parser.add_argument("--url", required=True, help="Page URL to fetch")
    parser.add_argument("--tag", default="product-slider", help="Container tag name (default: product-slider)")
    parser.add_argument("--id", default="Product-Slider", help="Container id (default: Product-Slider)")
    parser.add_argument("--show-html", action="store_true", help="Print full container HTML")
    parser.add_argument("--download", action="store_true", help="Download each stripped .jpg URL")
    parser.add_argument("--out", default="downloaded_images", help="Output directory for downloads")
    args = parser.parse_args()

    html = fetch_html(args.url)
    container = find_container(html, args.tag, args.id)

    if args.show_html:
        if container:
            print("----- FULL CONTAINER HTML START -----")
            print(container.prettify())
            print("----- FULL CONTAINER HTML END -----")
        else:
            print(f"Container <{args.tag} id='{args.id}'> not found.")

    images = extract_image_srcs(html, args.tag, args.id)
    print(f"Container <{args.tag} id='{args.id}'>: {len(images)} img src values found")
    for i, src in enumerate(images, 1):
        print(f"{i}. {src}")

    if args.download and images:
        download_images(images, args.out)

def download_images(urls: list[str], out_dir: str):
    import os
    os.makedirs(out_dir, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0"}
    for i, u in enumerate(urls, 1):
        original = u.rsplit('/',1)[-1]
        # Remove .jpg to append index after name
        if original.lower().endswith('.jpg'):
            stem = original[:-4]
            filename = f"{stem}_{i}.jpg"
        else:
            filename = f"{original}_{i}"  # fallback if no .jpg
        path = os.path.join(out_dir, filename)
        try:
            resp = requests.get(u, timeout=30, headers=headers)
            resp.raise_for_status()
            with open(path, "wb") as f:
                f.write(resp.content)
            print(f"Saved {filename}")
        except Exception as e:
            print(f"Failed {u}: {e}")

if __name__ == "__main__":
    main()