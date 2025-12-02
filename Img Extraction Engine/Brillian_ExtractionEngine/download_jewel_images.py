import os
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def fetch_html(url):
    resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.text

def extract_img_srcs(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    # container = soup.find("div", class_="swiper-wrapper")
    container = soup.find("div", class_="product__media-item") #limelight
    if not container:
        return []
    img_srcs = []
    for img in container.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        # Normalize relative URLs
        src = urljoin(base_url, src)
        # Only keep up to .jpg/.png/.webp
        m = re.search(r"(.+?\.(jpg|png|webp))", src, re.IGNORECASE)
        if m:
            img_srcs.append(m.group(1))
    return img_srcs

def download_images(img_urls, out_dir, product_id):
    os.makedirs(out_dir, exist_ok=True)
    for idx, url in enumerate(img_urls, 1):
        filename = f"{product_id}_{idx}.jpg"
        path = os.path.join(out_dir, filename)
        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            with open(path, "wb") as f:
                f.write(resp.content)
            print(f"Saved {filename}")
        except Exception as e:
            print(f"Failed to download {url}: {e}")

def process_excel(excel_path):
    df = pd.read_excel(excel_path)
    for _, row in df.iterrows():
        url = row["Source Link"]
        product_id = str(row["Product_Id"])
        print(f"Processing Product_Id={product_id} URL={url}")
        try:
            html = fetch_html(url)
            img_urls = extract_img_srcs(html, url)
            print(f"Found {len(img_urls)} images for Product_Id={product_id}")
            if img_urls:
                out_dir = os.path.join("download Jewel Img", product_id)
                download_images(img_urls, out_dir, product_id)
        except Exception as e:
            print(f"Error processing {url}: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download product images from Excel list.")
    parser.add_argument("--excel", required=True, help="Path to Excel file with product URLs and IDs.")
    args = parser.parse_args()
    process_excel(args.excel)

if __name__ == "__main__":
    main()
