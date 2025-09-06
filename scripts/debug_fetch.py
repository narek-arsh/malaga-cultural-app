# scripts/debug_fetch.py
import os, re, json, argparse, requests
from datetime import datetime
from pathlib import Path
from yaml import safe_load

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)

def fetch(url: str) -> requests.Response:
    return requests.get(
        url,
        headers={
            "User-Agent": UA,
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Referer": url.rsplit("/",1)[0] + "/",
        },
        timeout=60,
    )

def discover_activity_links(html: str, base_host: str):
    text = html.replace("\\/", "/")  # desescapa JSON embebido
    links = set()

    # href directos
    for m in re.finditer(r'href=["\'](https?://[^"\']+|/actividades/[^\s"\'>]+)["\']', text, flags=re.I):
        href = m.group(1)
        links.add(href)

    # rutas en scripts/JSON embebido
    for m in re.finditer(r'(/actividades/[a-z0-9\-/]+)', text, flags=re.I):
        links.add(m.group(1))

    norm = []
    for u in links:
        if u.lower().startswith("http"):
            norm.append(u)
        else:
            norm.append(base_host.rstrip("/") + u)
    # quita índice general
    norm = [u for u in norm if not re.match(r"https?://[^/]+/actividades/?$", u, flags=re.I)]
    return sorted(set(norm))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["picasso","thyssen","pompidou","all"], default="picasso",
                    help="Qué institución debuggear (por defecto: picasso)")
    args = ap.parse_args()

    # lee config
    with open("config/feeds.yaml", "r", encoding="utf-8") as f:
        cfg = safe_load(f)

    out_dir = Path("data/debug")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    targets = []
    for inst in cfg.get("institutions", []):
        iid = inst["id"]
        if args.only != "all" and iid != args.only:
            continue
        url = inst.get("urls", {}).get("activities_list")
        if not url:
            continue
        targets.append((iid, url))

    for iid, url in targets:
        host = re.match(r"^https?://[^/]+", url).group(0)
        print(f"[debug] fetching {iid} activities: {url}")
        try:
            r = fetch(url)
            html = r.text
            links = discover_activity_links(html, host)

            # guarda HTML y un resumen JSON
            html_path = out_dir / f"{iid}_activities_{ts}.html"
            info_path = out_dir / f"{iid}_activities_{ts}.json"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump({
                    "fetched_at": ts,
                    "url": url,
                    "status_code": r.status_code,
                    "encoding": r.encoding,
                    "headers_sample": dict(list(r.headers.items())[:20]),
                    "discovered_links_count": len(links),
                    "discovered_links": links[:200],  # por si hay muchísimos
                }, f, ensure_ascii=False, indent=2)

            print(f"[debug] saved: {html_path} ({len(html)} bytes)")
            print(f"[debug] links discovered: {len(links)} → {info_path}")

        except Exception as e:
            err_path = out_dir / f"{iid}_activities_{ts}.err.txt"
            with open(err_path, "w", encoding="utf-8") as f:
                f.write(str(e))
            print(f"[debug] ERROR {iid}: {e} (see {err_path})")

if __name__ == "__main__":
    main()
