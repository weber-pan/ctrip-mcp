#!/usr/bin/env python3
"""
ctrip-spa-capture extract_images
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

从抓好的 xhr_graphql_ProductInfo_2nd_V3_h5.json 提 4 类图片并下载到本地:
1. DescriptionInfo.Introduction HTML 里的 <img>(2 张 banner)
2. imageStyleInfo.poiInfo.ImagePoiList[].imgUrl(9 张 POI)
3. expertInfo.datas[].coverImageUrl(3 张社区攻略封面)
4. PMRecomendInfo.PMPicturesUrl(1 张产品经理照片)

用法:
    python extract_images.py <product_id> [--data-dir /opt/data/ctrip-data]
    # 产物: <data-dir>/img_<product_id>/{desc,poi,expert,pm}_*.jpg
    # 落盘: manifest.json (url→本地路径映射, 报告直接引用)

输出:
    - 下载成功 15/15 典型 (p42461732 实测)
    - manifest.json 列出 url / local_path / source_field / alt_text
"""
import json
import re
import os
import sys
import subprocess
import argparse
from pathlib import Path


def extract_all(product_id: int, data_dir: str) -> dict:
    """从 ProductInfo_2nd_V3_h5.json 提所有图 URL + alt"""
    fn = Path(data_dir) / f"xhr_graphql_ProductInfo_2nd_V3_h5_{product_id}.json"
    if not fn.exists():
        # 兼容老文件名 (无 _pid 后缀)
        fn = Path(data_dir) / "xhr_graphql_ProductInfo_2nd_V3_h5.json"
    if not fn.exists():
        raise FileNotFoundError(f"未找到 {fn} (先跑 ctrip_spa_capture.py)")

    j = json.load(open(fn))
    pi = j["data"]["productInfo"]
    imgs = []  # [(source, url, alt)]

    # 1) DescriptionInfo.Introduction HTML
    intro = pi.get("DescriptionInfo", {}).get("Introduction", "") or ""
    for u in re.findall(r'<img[^>]*src="([^"]+)"', intro):
        m = re.search(r'title="([^"]+)"', intro[intro.find(u):])
        alt = m.group(1) if m else ""
        imgs.append(("desc", u, alt))

    # 2) POI
    poi_list = pi.get("imageStyleInfo", {}).get("poiInfo", {}).get("ImagePoiList", [])
    for p in poi_list:
        name = p.get("name", "unknown")
        url = p.get("imgUrl", "")
        if url:
            imgs.append((f"poi_{name}", url, name))

    # 3) expertInfo.datas[].coverImageUrl
    for i, d in enumerate(pi.get("expertInfo", {}).get("datas", [])):
        url = d.get("coverImageUrl", "")
        if url:
            imgs.append((f"expert_{i}", url, d.get("title", "")[:60]))

    # 4) PMRecomendInfo.PMPicturesUrl
    pmr = pi.get("PMRecomendInfo", {})
    if pmr.get("PMPicturesUrl"):
        imgs.append(("pm", pmr["PMPicturesUrl"], "产品经理"))

    return imgs


def download_imgs(imgs: list, out_dir: Path) -> list:
    """下载 + 落盘 manifest"""
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    ok = 0
    for tag, url, alt in imgs:
        if not url:
            continue
        # 安全文件名
        safe_tag = re.sub(r'[^\w\-_]', '_', tag)[:30]
        ext = ".jpg"
        for e in (".jpg", ".jpeg", ".png", ".webp"):
            if e in url.lower():
                ext = e
                break
        fn = out_dir / f"{safe_tag}{ext}"
        try:
            r = subprocess.run(
                ["curl", "-sL", "-A", "Mozilla/5.0", "-o", str(fn), url],
                capture_output=True, timeout=30,
            )
            sz = fn.stat().st_size if fn.exists() else 0
            if sz > 1000:
                ok += 1
                status = "ok"
            else:
                status = "too_small"
        except Exception as e:
            sz = 0
            status = f"err:{e}"
        manifest.append({
            "tag": tag, "url": url, "alt": alt, "ext": ext,
            "local_path": str(fn), "size": sz, "status": status,
        })
    # 写 manifest
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest


def main():
    p = argparse.ArgumentParser(description="携程产品图片一键提取 (4 类源)")
    p.add_argument("product_id", type=int, help="携程 productId (e.g. 42461732)")
    p.add_argument("--data-dir", default="/opt/data/ctrip-data", help="xhr_*.json 落盘目录")
    args = p.parse_args()

    imgs = extract_all(args.product_id, args.data_dir)
    print(f"[extract] 提 URL: {len(imgs)} 张 (4 类源)")

    out_dir = Path(args.data_dir) / f"img_{args.product_id}"
    manifest = download_imgs(imgs, out_dir)

    ok = sum(1 for m in manifest if m["status"] == "ok")
    print(f"[download] 成功: {ok}/{len(manifest)} 张")
    print(f"[output] {out_dir}/")
    print(f"         manifest.json (url→本地路径映射)")
    # 简短分类打印
    by_source = {}
    for m in manifest:
        s = m["tag"].split("_")[0]
        by_source.setdefault(s, 0)
        if m["status"] == "ok":
            by_source[s] += 1
    for src, cnt in by_source.items():
        print(f"  {src:10} {cnt} 张")


if __name__ == "__main__":
    main()
