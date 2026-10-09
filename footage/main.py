"""
main.py: work footage library (FOOTAGE_HANDOFF.md, Drive Footage Pipeline/). Phase 0 only so far.
    python main.py check                         # hardware: GPU, ffprobe, dell-node, OneDrive roots
    python main.py inventory [--root DIR ...] [--out E:\\Footage] [--probe-cloud]
Rules:
  - Read-only on OneDrive. Nothing is moved, renamed, written, or deleted under a root. The output
    folder must sit outside every root or the run stops.
  - Cloud-only files (OneDrive placeholders) are counted from their metadata and NOT probed, because
    opening one makes the sync client download it. --probe-cloud overrides that (pulls them down).
  - Probe results are cached in <out>/cache/probe.json keyed by path, size, and mtime, so reruns
    only probe new or changed files.
Writes <out>/inventory.csv (one row per video) and <out>/inventory_report.txt (the Phase 0 report).
Later commands (process, label, test, classify, cut, report) land here as their phases start.
"""
import argparse, csv, datetime, json, os, re, shutil, subprocess, sys
from collections import Counter

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".mts", ".m2ts", ".3gp", ".wmv", ".mpg", ".mpeg", ".webm", ".lrv", ".insv", ".360"}
# Windows file attribute bits the OneDrive client sets on placeholders.
ATTR_OFFLINE, ATTR_RECALL_ON_OPEN, ATTR_RECALL_ON_DATA = 0x1000, 0x40000, 0x400000
ATTR_PINNED, ATTR_UNPINNED = 0x80000, 0x100000
# Phase 0 time model. Rough on purpose; the pilot measures the real numbers and replaces these.
WHISPER_RT = {"gpu": 0.05, "cpu": 1.0}      # processing seconds per second of audio, small model, int8
CAPTION_SEC = {"gpu": 0.3, "cpu": 2.5}      # seconds per keyframe, Florence-2 base class
SCENES_PER_MIN, FRAMES_PER_SCENE = 4, 3
NAME_DATE = re.compile(r"(?<!\d)(20\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])(?!\d)")


def onedrive_roots():
    """Every OneDrive root the sync client advertises, tagged work or personal."""
    seen, out = set(), []
    for var, kind in (("OneDriveCommercial", "work"), ("OneDriveConsumer", "personal"), ("OneDrive", "default")):
        p = os.environ.get(var)
        if p and os.path.isdir(p) and os.path.normcase(p) not in seen:
            seen.add(os.path.normcase(p)); out.append((p, kind))
    home = os.path.expanduser("~")
    for name in sorted(os.listdir(home)) if os.path.isdir(home) else []:
        p = os.path.join(home, name)
        if name.startswith("OneDrive") and os.path.isdir(p) and os.path.normcase(p) not in seen:
            seen.add(os.path.normcase(p)); out.append((p, "work" if " - " in name else "personal"))
    return out


def inside(child, parent):
    c, p = os.path.normcase(os.path.abspath(child)), os.path.normcase(os.path.abspath(parent))
    return c == p or c.startswith(p.rstrip("\\/") + os.sep)


def cloud_state(st):
    """'local', 'cloud' (placeholder, not on disk), or 'pinned'. Non-Windows is always local."""
    a = getattr(st, "st_file_attributes", 0)
    if a & (ATTR_RECALL_ON_DATA | ATTR_RECALL_ON_OPEN | ATTR_OFFLINE):
        return "cloud"
    return "pinned" if a & ATTR_PINNED else "local"


def walk_videos(root):
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for f in files:
            if os.path.splitext(f)[1].lower() in VIDEO_EXT:
                yield os.path.join(dirpath, f)


def ffprobe(path):
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    except subprocess.TimeoutExpired:
        return {"error": "ffprobe timeout"}
    if r.returncode:
        return {"error": " ".join((r.stderr or "ffprobe failed").split())[-200:]}
    j = json.loads(r.stdout or "{}")
    fmt, streams = j.get("format", {}), j.get("streams", [])
    tags = {k.lower(): v for k, v in fmt.get("tags", {}).items()}
    for s in streams:
        for k, v in s.get("tags", {}).items():
            tags.setdefault(k.lower(), v)
    vid = next((s for s in streams if s.get("codec_type") == "video"), {})
    gps = tags.get("com.apple.quicktime.location.iso6709") or tags.get("location") or tags.get("location-eng") or ""
    return {
        "duration": float(fmt.get("duration") or 0),
        "width": vid.get("width"), "height": vid.get("height"), "vcodec": vid.get("codec_name", ""),
        "audio": any(s.get("codec_type") == "audio" for s in streams),
        "created": tags.get("com.apple.quicktime.creationdate") or tags.get("creation_time") or "",
        "gps": gps.strip("/"),
    }


def pick_date(probe, path, mtime):
    """Best capture date and where it came from: metadata, filename, then file mtime."""
    c = (probe or {}).get("created", "")
    if c[:4].isdigit() and not c.startswith(("1904", "1970")):
        return c[:10], "meta"
    m = NAME_DATE.search(os.path.basename(path))
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}", "name"
    return datetime.date.fromtimestamp(mtime).isoformat(), "mtime"


def hms(sec):
    sec = int(sec)
    return f"{sec // 3600}h {sec % 3600 // 60:02d}m"


def gb(n):
    return f"{n / 1e9:,.1f} GB"


def has_gpu():
    if not shutil.which("nvidia-smi"):
        return ""
    r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def cmd_check(args):
    gpu = has_gpu()
    print(f"GPU:       {gpu or 'none found (nvidia-smi missing or failed)'}")
    print(f"ffprobe:   {shutil.which('ffprobe') or 'NOT FOUND, install ffmpeg and put it on PATH'}")
    print(f"ffmpeg:    {shutil.which('ffmpeg') or 'NOT FOUND'}")
    for host in ("dell-node", "hp-node"):
        try:
            r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", host, "echo up; nproc; free -g | sed -n 2p"],
                               capture_output=True, text=True, timeout=15)
            out = " | ".join(r.stdout.split("\n")).strip(" |") if r.returncode == 0 else f"down ({r.stderr.strip()[:80]})"
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            out = f"down ({type(e).__name__})"
        print(f"{host + ':':10} {out}")
    roots = onedrive_roots()
    if not roots:
        print("OneDrive:  no roots found; pass --root to inventory")
    for p, kind in roots:
        print(f"OneDrive:  [{kind}] {p}")


def cmd_inventory(args):
    roots = [(r, "given") for r in args.root] if args.root else onedrive_roots()
    if not roots:
        sys.exit("no OneDrive root found; pass --root <folder>")
    out = os.path.abspath(args.out)
    for r, _ in roots:
        if not os.path.isdir(r):
            sys.exit(f"root not found: {r}")
        if inside(out, r):
            sys.exit(f"output {out} is inside {r}; pick an output folder outside OneDrive")
    os.makedirs(os.path.join(out, "cache"), exist_ok=True)
    cache_path = os.path.join(out, "cache", "probe.json")
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}
    if not shutil.which("ffprobe"):
        print("ffprobe not found: durations will be missing. Install ffmpeg and rerun.", file=sys.stderr)

    rows, probed = [], 0
    for root, kind in roots:
        for path in walk_videos(root):
            try:
                st = os.stat(path)
            except OSError as e:
                print(f"skip {path}: {e}", file=sys.stderr); continue
            state = cloud_state(st)
            key = f"{path}|{st.st_size}|{int(st.st_mtime)}"
            probe = cache.get(key)
            if probe is None and shutil.which("ffprobe") and (state != "cloud" or args.probe_cloud):
                probe = cache[key] = ffprobe(path)
                probed += 1
                if probed % 50 == 0:
                    json.dump(cache, open(cache_path, "w", encoding="utf-8"))
                    print(f"  probed {probed} ...", file=sys.stderr)
            probe = probe or {}
            date, date_src = pick_date(probe, path, st.st_mtime)
            rows.append({
                "root_kind": kind, "path": path, "rel": os.path.relpath(path, root), "ext": os.path.splitext(path)[1].lower(),
                "size": st.st_size, "state": state, "date": date, "date_src": date_src,
                "duration": round(probe.get("duration", 0), 2) if "duration" in probe else "",
                "width": probe.get("width") or "", "height": probe.get("height") or "", "vcodec": probe.get("vcodec", ""),
                "audio": {True: "yes", False: "no"}.get(probe.get("audio"), ""), "gps": probe.get("gps", ""),
                "error": probe.get("error", ""),
            })
    json.dump(cache, open(cache_path, "w", encoding="utf-8"))

    with open(os.path.join(out, "inventory.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["path"])
        w.writeheader(); w.writerows(rows)
    report = build_report(rows, roots, "gpu" if has_gpu() else "cpu")
    open(os.path.join(out, "inventory_report.txt"), "w", encoding="utf-8").write(report)
    print(report)
    print(f"\nwrote {os.path.join(out, 'inventory.csv')} and inventory_report.txt ({probed} newly probed)")


def build_report(rows, roots, hw):
    L = [f"Footage inventory, {datetime.date.today().isoformat()}", ""]
    L += [f"Root [{k}]: {r}" for r, k in roots] + [""]
    if not rows:
        return "\n".join(L + ["No video files found."])
    total = sum(r["size"] for r in rows)
    timed = [r for r in rows if r["duration"] != ""]
    known_sec = sum(r["duration"] for r in timed)
    known_bytes = sum(r["size"] for r in timed)
    untimed_bytes = total - known_bytes
    # Untimed files (cloud-only or probe errors) get hours from the average bitrate of the timed ones.
    est_sec = known_sec + (untimed_bytes * known_sec / known_bytes if known_bytes else 0)
    states = Counter(r["state"] for r in rows)
    dates = sorted(r["date"] for r in rows)
    L.append(f"Videos:      {len(rows):,}")
    L.append(f"Total size:  {gb(total)}")
    L.append(f"Total hours: {hms(known_sec)} measured on {len(timed):,} files"
             + (f"; about {hms(est_sec)} including {len(rows) - len(timed):,} unmeasured (bitrate estimate)" if len(timed) < len(rows) else ""))
    L.append(f"Date range:  {dates[0]} to {dates[-1]}")
    L.append("Dates from:  " + ", ".join(f"{k} {v:,}" for k, v in Counter(r['date_src'] for r in rows).most_common()))
    L.append("On disk:     " + ", ".join(f"{k} {v:,}" for k, v in states.most_common())
             + f"  (cloud-only size {gb(sum(r['size'] for r in rows if r['state'] == 'cloud'))})")
    L.append("Formats:     " + ", ".join(f"{k} {v:,}" for k, v in Counter(r['ext'] for r in rows).most_common()))
    codecs = Counter(r["vcodec"] for r in timed if r["vcodec"])
    if codecs:
        L.append("Codecs:      " + ", ".join(f"{k} {v:,}" for k, v in codecs.most_common()))
    L.append(f"With audio:  {sum(r['audio'] == 'yes' for r in rows):,}   with GPS: {sum(bool(r['gps']) for r in rows):,}")
    errs = [r for r in rows if r["error"]]
    if errs:
        L.append(f"Probe errors: {len(errs):,} (see error column in inventory.csv)")
    L.append("")
    L.append("Per year: count, size, hours")
    by_year = {}
    for r in rows:
        y = by_year.setdefault(r["date"][:4], [0, 0, 0.0]); y[0] += 1; y[1] += r["size"]; y[2] += r["duration"] or 0
    for y in sorted(by_year):
        c, s, d = by_year[y]
        L.append(f"  {y}  {c:6,}  {gb(s):>10}  {hms(d)}")
    L.append("")
    L.append("Per top folder: count, size")
    by_top = Counter(); by_top_b = Counter()
    for r in rows:
        top = r["rel"].split(os.sep)[0] if os.sep in r["rel"] else "(root)"
        by_top[top] += 1; by_top_b[top] += r["size"]
    for top, c in by_top.most_common(25):
        L.append(f"  {c:6,}  {gb(by_top_b[top]):>10}  {top}")
    audio_share = sum(r["audio"] == "yes" for r in timed) / len(timed) if timed else 1.0
    whisper = est_sec * audio_share * WHISPER_RT[hw]
    caption = est_sec / 60 * SCENES_PER_MIN * FRAMES_PER_SCENE * CAPTION_SEC[hw]
    L.append("")
    L.append(f"Time estimate on {hw.upper()} (rough, replaced by pilot measurements):")
    L.append(f"  Whisper small int8: {hms(whisper)}  ({WHISPER_RT[hw]}x real time on files with audio; VAD will cut this)")
    L.append(f"  Captions:           {hms(caption)}  ({SCENES_PER_MIN} scenes/min, {FRAMES_PER_SCENE} frames/scene, {CAPTION_SEC[hw]} s/frame)")
    if hw == "cpu":
        L.append(f"  Split over dell-node + hp-node: about {hms((whisper + caption) / 2)} wall clock")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1].strip())
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="GPU, ffprobe, worker nodes, OneDrive roots")
    p = sub.add_parser("inventory", help="Phase 0: count and size every video under the OneDrive roots")
    p.add_argument("--root", action="append", default=[], help="folder to inventory (repeatable); default is every OneDrive root")
    p.add_argument("--out", default=r"E:\Footage" if os.name == "nt" else os.path.expanduser("~/Footage"))
    p.add_argument("--probe-cloud", action="store_true", help="also probe cloud-only files (this downloads them)")
    args = ap.parse_args()
    {"check": cmd_check, "inventory": cmd_inventory}[args.cmd](args)


if __name__ == "__main__":
    main()
