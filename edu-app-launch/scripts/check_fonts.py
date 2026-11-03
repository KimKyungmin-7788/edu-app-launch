#!/usr/bin/env python3
"""교육용 웹앱의 폰트 라이선스를 점검한다.

하는 일
  1. 앱 폴더 안의 폰트 파일(.ttf .otf .woff .woff2)을 모두 찾는다.
  2. 폰트 파일 안에 적힌 이름·저작권·라이선스 정보를 읽는다(ttf/otf/woff).
  3. 같은 폴더(또는 상위 폴더)에 OFL.txt 같은 라이선스 파일이 있는지 본다.
  4. 코드(html/css/js/ts/jsx/tsx/vue/svelte)에서 외부 폰트 주소와 font-family 이름을 모은다.
  5. 결과를 '통과 / 확인 필요 / 조치 필요'로 나눠 보여 준다.

외부 패키지 없이 파이썬 표준 라이브러리만 쓴다.
사용법: python3 check_fonts.py <앱폴더>
"""
import os
import re
import struct
import sys
import zlib

FONT_EXT = ('.ttf', '.otf', '.woff', '.woff2')
CODE_EXT = ('.html', '.htm', '.css', '.scss', '.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte', '.mjs')
SKIP_DIRS = {'node_modules', '.git', '.vercel', '.next', '.netlify', '.cache', '__pycache__'}
LICENSE_NAMES = re.compile(r'^(ofl|license|licence|copying|font[-_]?license)[^/]*\.(txt|md)$|^(ofl|license|licence)$', re.I)
OFL_HINT = re.compile(r'open font license|scripts\.sil\.org/ofl|openfontlicense\.org|\bOFL\b', re.I)
KOGL_HINT = re.compile(r'공공누리|KOGL|kogl\.or\.kr', re.I)
SCHOOL_SAFE_HINT = re.compile(r'학교\s*안심|hakgyoansim|KERIS', re.I)


# ---------- 폰트 파일 안의 name 테이블 읽기 ----------

def _sfnt_tables(data):
    """ttf/otf 바이트에서 {태그: 바이트} 반환."""
    num = struct.unpack('>H', data[4:6])[0]
    tables = {}
    for i in range(num):
        tag, _, off, length = struct.unpack('>4sIII', data[12 + 16 * i: 28 + 16 * i])
        tables[tag.decode('latin-1')] = data[off: off + length]
    return tables


def _woff_tables(data):
    """woff(1) 바이트에서 {태그: 바이트} 반환. woff2는 brotli가 필요해 지원하지 않는다."""
    num = struct.unpack('>H', data[12:14])[0]
    tables = {}
    for i in range(num):
        tag, off, comp_len, orig_len, _ = struct.unpack('>4sIIII', data[44 + 20 * i: 64 + 20 * i])
        raw = data[off: off + comp_len]
        tables[tag.decode('latin-1')] = zlib.decompress(raw) if comp_len < orig_len else raw
    return tables


def read_names(path):
    """폰트의 name 테이블에서 주요 항목을 읽는다. 읽을 수 없으면 None."""
    try:
        data = open(path, 'rb').read()
        sig = data[:4]
        if sig == b'wOFF':
            tables = _woff_tables(data)
        elif sig in (b'\x00\x01\x00\x00', b'OTTO', b'true'):
            tables = _sfnt_tables(data)
        else:
            return None  # woff2 등
        name = tables.get('name')
        if not name:
            return {}
        _, count, str_off = struct.unpack('>HHH', name[:6])
        out = {}
        for i in range(count):
            pid, eid, lid, nid, length, off = struct.unpack('>HHHHHH', name[6 + 12 * i: 18 + 12 * i])
            if nid not in (0, 1, 4, 13, 14):
                continue
            raw = name[str_off + off: str_off + off + length]
            try:
                text = raw.decode('utf-16-be') if pid in (0, 3) else raw.decode('mac_roman')
            except UnicodeDecodeError:
                continue
            # 한국어(0x0412)·영어 이름을 우선, 이미 있으면 유지
            if nid not in out or lid == 0x0412:
                out[nid] = text.strip()
        return out
    except Exception:
        return None


# ---------- 폴더 훑기 ----------

def walk(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            yield os.path.join(d, f)


def find_license(font_path, root):
    """폰트가 있는 폴더부터 앱 루트까지 올라가며 라이선스 파일을 찾는다."""
    d = os.path.dirname(font_path)
    root = os.path.abspath(root)
    while True:
        try:
            for f in os.listdir(d):
                if LICENSE_NAMES.match(f):
                    return os.path.join(d, f)
        except OSError:
            pass
        if os.path.abspath(d) == root or len(d) <= len(root):
            return None
        d = os.path.dirname(d)


def deploy_hint(rel):
    """배포 결과물에 라이선스 파일이 따라가는지 판단하는 데 쓰는 위치 힌트."""
    parts = rel.replace('\\', '/').split('/')
    if parts[0] in ('dist', 'build', 'out'):
        return '빌드 결과물'
    if parts[0] == 'public':
        return 'public(그대로 배포됨)'
    if parts[0] == 'src':
        return 'src(빌드 시 이름이 바뀌어 복사됨)'
    return '앱 폴더'


def scan_code(root):
    ext_urls, families, faces = set(), set(), []
    url_re = re.compile(r'https?://[^\s"\'()<>]+')
    fam_re = re.compile(r'font-family\s*:\s*([^;}{]+)', re.I)
    js_fam_re = re.compile(r'fontFamily\s*:\s*[\'"`]([^\'"`]+)', re.I)
    face_src_re = re.compile(r'@font-face\s*{[^}]*?src\s*:\s*([^;]+)', re.I | re.S)
    font_url_hint = re.compile(r'font|woff|ttf|otf|typekit|pretendard|noonnu|gstatic|googleapis', re.I)
    for p in walk(root):
        if not p.lower().endswith(CODE_EXT):
            continue
        rel = os.path.relpath(p, root)
        if rel.split(os.sep)[0] in ('dist', 'build', 'out'):
            continue
        try:
            text = open(p, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        for u in url_re.findall(text):
            if font_url_hint.search(u):
                ext_urls.add((u.rstrip(';,'), rel))
        for m in fam_re.findall(text) + js_fam_re.findall(text):
            for name in m.split(','):
                name = name.strip().strip('\'"` ').replace('!important', '').strip()
                if name and not name.startswith(('var(', 'inherit', 'initial', '$')):
                    families.add(name)
        for src in face_src_re.findall(text):
            faces.append((src.strip()[:120], rel))
    return ext_urls, families, faces


GENERIC = {'sans-serif', 'serif', 'monospace', 'cursive', 'fantasy', 'system-ui', 'ui-sans-serif',
           'ui-serif', 'ui-monospace', '-apple-system', 'blinkmacsystemfont', 'segoe ui', 'roboto',
           'helvetica', 'helvetica neue', 'arial', 'apple sd gothic neo', 'malgun gothic', '맑은 고딕',
           'noto sans kr', 'noto sans', 'apple color emoji', 'segoe ui emoji', 'segoe ui symbol',
           'noto color emoji', 'inherit'}


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
    print(f'== 폰트 라이선스 점검: {root} ==\n')
    ok, check, fix = [], [], []

    fonts = [p for p in walk(root) if p.lower().endswith(FONT_EXT)]
    print(f'[1] 앱 안의 폰트 파일: {len(fonts)}개')
    for p in fonts:
        rel = os.path.relpath(p, root)
        names = read_names(p)
        lic = find_license(p, root)
        lic_text = ''
        if lic:
            try:
                lic_text = open(lic, encoding='utf-8', errors='ignore').read(20000)
            except OSError:
                pass
        meta = ' '.join((names or {}).get(k, '') for k in (0, 13, 14))
        family = (names or {}).get(1) or (names or {}).get(4) or '(이름 읽기 불가)'
        is_ofl = bool(OFL_HINT.search(meta) or OFL_HINT.search(lic_text))
        is_kogl = bool(KOGL_HINT.search(meta) or KOGL_HINT.search(lic_text))
        is_school = bool(SCHOOL_SAFE_HINT.search(meta + ' ' + family + ' ' + rel))
        print(f'  - {rel}')
        print(f'      글꼴 이름: {family}   위치: {deploy_hint(rel)}')
        if names and names.get(0):
            print(f'      저작권 표기: {names[0][:100].replace(chr(10), " ")}')
        if names and names.get(13):
            print(f'      라이선스 표기: {names[13][:100].replace(chr(10), " ")}')
        if names is None and p.lower().endswith('.woff2'):
            print('      (woff2는 내부 정보를 읽지 않음 — 라이선스 파일로 판단)')
        print(f'      라이선스 파일: {os.path.relpath(lic, root) if lic else "없음"}')

        if is_kogl:
            fix.append(f'{rel}: 공공누리(KOGL) 표기 발견 — 출처표시 의무가 있는 유형일 수 있음. 조건 확인 후 앱 안에 출처를 표시하거나 OFL 폰트로 교체')
        elif is_ofl and lic:
            ok.append(f'{rel}: OFL 확인, 라이선스 파일 있음')
            if deploy_hint(rel).startswith('src'):
                check.append(f'{rel}: src 안의 폰트는 빌드 때 다른 이름으로 복사되고 라이선스 파일은 따라가지 않음 — 라이선스 파일을 public/fonts/ 등 배포되는 위치에도 두기')
        elif is_ofl and not lic:
            fix.append(f'{rel}: OFL 폰트인데 라이선스 파일(OFL.txt)이 없음 — 폰트를 받을 때 들어 있던 OFL.txt를 같은 폴더에 넣기')
        elif is_school and not lic:
            fix.append(f'{rel}: 학교안심 글꼴로 보이나 라이선스 파일이 없음 — KERIS 묶음에는 OFL.txt가 없으니 학교안심 글꼴 키트(https://github.com/KimKyungmin-7788/hakgyoansim-font-kit)의 fonts/OFL.txt를 같은 폴더에 넣기')
        else:
            check.append(f'{rel}: 라이선스를 확인할 수 없음 — 받은 곳(공식 배포처)에서 라이선스가 OFL인지 확인. 모르면 학교안심 글꼴로 교체')

    ext_urls, families, faces = scan_code(root)
    print(f'\n[2] 코드에서 불러오는 외부 폰트 주소: {len(ext_urls)}개')
    for u, rel in sorted(ext_urls):
        print(f'  - {u}   ({rel})')
        if 'fonts.googleapis.com' in u or 'fonts.gstatic.com' in u:
            check.append(f'Google Fonts 사용({rel}) — 해당 글꼴의 라이선스(대부분 OFL)를 fonts.google.com 글꼴 페이지에서 확인. 폰트 파일을 직접 배포하는 게 아니어서 OFL.txt는 필요 없음. CSP에 fonts.googleapis.com·fonts.gstatic.com 허용 필요')
        else:
            check.append(f'외부 폰트 주소 {u} — 제공처와 라이선스를 확인하고, CSP의 style-src/font-src에 도메인 추가 여부 확인')

    print(f'\n[3] @font-face 선언: {len(faces)}개')
    for s, rel in faces:
        print(f'  - {s}   ({rel})')

    used = sorted(f for f in families if f.lower() not in GENERIC)
    print(f'\n[4] font-family로 쓰는 글꼴 이름: {", ".join(used) if used else "(시스템 기본 글꼴만)"}')
    if used:
        check.append('위 [4]의 글꼴 이름이 [1]·[2]에서 모두 출처가 확인되는지 대조 (컴퓨터에 설치된 유료 폰트 이름만 적혀 있으면 학생 기기에선 안 보이고, 이미지로 구워 넣었다면 라이선스 문제가 될 수 있음)')

    print('\n== 결과 ==')
    for title, items in (('통과', ok), ('확인 필요', check), ('조치 필요', fix)):
        print(f'[{title}] {len(items)}건')
        for i in dict.fromkeys(items):
            print(f'  - {i}')
    sys.exit(1 if fix else 0)


if __name__ == '__main__':
    main()
