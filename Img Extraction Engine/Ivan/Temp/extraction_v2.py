import os
import argparse
import requests
from bs4 import BeautifulSoup

DEFAULT_URL = "https://ivanajewels.com/products/0-75-carat-lab-grown-diamond-studs"

def normalize(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    return url

def strip_to_jpg(url: str) -> str:
    idx = url.lower().find(".jpg")
    return url[:idx+4] if idx != -1 else url

def get_slider_imgs(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    slider = soup.find(id="Product-Slider")
    if not slider:
        return []
    found: list[str] = []
    seen = set()
    for img in slider.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        if src.startswith("data:"):
            # Skip inline base64 placeholders
            continue
        src = normalize(src)
        base = strip_to_jpg(src)
        if base not in seen:
            seen.add(base)
            found.append(base)
    return found

def download_images(urls: list[str], out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0"}
    for i, u in enumerate(urls, start=1):
        full = u if u.startswith("http") else ("https:" + u if u.startswith("//") else u)
        filename = f"{i}_{full.rsplit('/',1)[-1]}"
        path = os.path.join(out_dir, filename)
        try:
            resp = requests.get(full, timeout=30, headers=headers)
            resp.raise_for_status()
            with open(path, "wb") as f:
                f.write(resp.content)
            print(f"Saved {filename}")
        except Exception as e:
            print(f"Failed {full}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Simple Product-Slider image extractor")
    parser.add_argument("--url", default=DEFAULT_URL, help="Product page URL")
    parser.add_argument("--file", help="Local HTML file ( overrides URL )")
    parser.add_argument("--download", action="store_true", help="Download images")
    parser.add_argument("--out", default="downloaded_images", help="Download directory")
    args = parser.parse_args()

    if args.file and os.path.isfile(args.file):
        html = open(args.file, "r", encoding="utf-8").read()
        page_id = args.file
    else:
        html = requests.get(args.url, timeout=30, headers={"User-Agent":"Mozilla/5.0"}).text
        page_id = args.url

    imgs = get_slider_imgs(html)
    print(f"Found {len(imgs)} images in Product-Slider on {page_id}")
    for i, u in enumerate(imgs, start=1):
        print(f"{i}. {u}")

    if args.download and imgs:
        print("Downloading images...")
        download_images(imgs, args.out)

if __name__ == "__main__":
    main()