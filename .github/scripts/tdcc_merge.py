"""把每天下載的集保開放資料（原始檔）合併成歷史檔。
- 自動判斷編碼（UTF-8 / UTF-8-BOM / Big5）
- 淨值 3-4：依「基金代碼＋日期」去重，累積到 data/tdcc/nav.csv
- 配息 3-5：整列去重，累積到 data/tdcc/dividend.csv
- 基本資料 3-2：保留最新一份 data/tdcc/basic.csv
原始檔一律保留在 data/tdcc/raw/，格式有變也不會遺失。
"""
import csv, io, os, glob, json

BASE = 'data/tdcc'

def read(path):
    b = open(path, 'rb').read()
    for enc in ('utf-8-sig', 'big5', 'cp950'):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            pass
    return b.decode('utf-8', 'replace'), 'utf-8?'

def rows(path):
    txt, enc = read(path)
    txt = txt.strip()
    if txt.startswith('[') or txt.startswith('{'):
        data = json.loads(txt)
        if isinstance(data, dict):
            data = next((v for v in data.values() if isinstance(v, list)), [data])
        hdr = list(data[0].keys()) if data else []
        return hdr, [[str(d.get(h, '')) for h in hdr] for d in data], enc
    r = list(csv.reader(io.StringIO(txt)))
    r = [x for x in r if any(c.strip() for c in x)]
    return (r[0] if r else []), r[1:], enc

def merge(fid, out, key_cols=None, latest_only=False):
    files = sorted(glob.glob(f'{BASE}/raw/*/{fid}.csv'))
    if not files:
        print(fid, '尚無原始檔'); return
    hdr, seen, allrows = None, set(), []
    if latest_only:
        files = files[-1:]
    elif os.path.exists(out):
        h, old, _ = rows(out)
        hdr = h
        for x in old:
            k = tuple(x[i] for i in key_cols) if key_cols else tuple(x)
            if k not in seen:
                seen.add(k); allrows.append(x)
    for f in files:
        h, rs, enc = rows(f)
        if not h:
            continue
        if hdr is None:
            hdr = h
        if h != hdr:
            print('欄位不同，略過合併（原始檔已保留）：', f, h); continue
        for x in rs:
            k = tuple(x[i] for i in key_cols) if key_cols else tuple(x)
            if k not in seen:
                seen.add(k); allrows.append(x)
    with open(out, 'w', newline='', encoding='utf-8') as fp:
        w = csv.writer(fp); w.writerow(hdr); w.writerows(allrows)
    print(fid, '→', out, len(allrows), '筆；欄位：', hdr)

def keycols(fid, names):
    files = sorted(glob.glob(f'{BASE}/raw/*/{fid}.csv'))
    if not files: return None
    h, _, _ = rows(files[-1])
    idx = [i for i, c in enumerate(h) if any(n in c for n in names)]
    return idx or None

merge('3-4', f'{BASE}/nav.csv', keycols('3-4', ['代碼', '代號', '日期']))
merge('3-5', f'{BASE}/dividend.csv')
merge('3-2', f'{BASE}/basic.csv', latest_only=True)
