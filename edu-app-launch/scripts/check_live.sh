#!/bin/bash
# 배포된 교육용 앱의 보안 헤더·방침 페이지·미리보기를 확인한다.
# 사용법: check_live.sh https://앱주소 [폰트 라이선스 경로 ...]
#   예: check_live.sh https://myapp.vercel.app /fonts/OFL.txt
set -u
URL="${1:-}"
[ -z "$URL" ] && { echo "사용법: $0 https://앱주소 [폰트 라이선스 경로 ...]"; exit 1; }
URL="${URL%/}"
shift

echo "== 페이지 응답 =="
for p in / /privacy /terms /og.png; do
  printf "  %-10s %s\n" "$p" "$(curl -s -o /dev/null -w '%{http_code} %{content_type}' "$URL$p")"
done

echo "== 보안 헤더 =="
H=$(curl -sI "$URL/" | tr -d '\r')
for k in content-security-policy x-frame-options x-content-type-options referrer-policy permissions-policy strict-transport-security; do
  v=$(echo "$H" | grep -i "^$k:" | cut -d' ' -f2-)
  if [ -n "$v" ]; then printf "  OK   %-26s %.70s\n" "$k" "$v"; else printf "  없음 %s\n" "$k"; fi
done
echo "$H" | grep -i '^access-control-allow-origin:' | sed 's/^/  참고 /'

echo "== 미리보기 메타 =="
B=$(curl -s "$URL/")
for m in 'name="description"' 'rel="canonical"' 'property="og:title"' 'property="og:image"'; do
  if echo "$B" | grep -q "$m"; then echo "  OK   $m"; else echo "  없음 $m"; fi
done
if echo "$B" | grep -q 'href="/privacy"'; then echo "  OK   첫 화면에 방침 링크"; else echo "  없음 첫 화면에 방침 링크"; fi

if [ $# -gt 0 ]; then
  echo "== 폰트 라이선스 파일 =="
  for p in "$@"; do
    c=$(curl -s -o /dev/null -w '%{http_code}' "$URL$p")
    if [ "$c" = "200" ]; then echo "  OK   $p"; else echo "  없음 $p ($c)"; fi
  done
fi
