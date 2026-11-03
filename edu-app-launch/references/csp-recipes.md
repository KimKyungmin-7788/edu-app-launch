# CSP 조합표

`templates/vercel.json`의 기본 CSP는 "우리 사이트 + cdnjs + Google Fonts"만 허용해요.
1단계에서 찾은 서비스에 맞춰 아래 값을 **해당 지시어에 덧붙인다**. 쓰지 않는 서비스는 빼요.

| 쓰는 것 | 덧붙일 곳 |
|---|---|
| Google Fonts | `style-src https://fonts.googleapis.com` · `font-src https://fonts.gstatic.com` |
| cdnjs | `script-src https://cdnjs.cloudflare.com` |
| jsDelivr | `script-src https://cdn.jsdelivr.net` (CSS도 쓰면 `style-src`에도) |
| unpkg | `script-src https://unpkg.com` |
| 앱 안에 둔 폰트 파일(셀프 호스팅) | 추가할 것 없음(`font-src 'self'`가 기본값). 라이선스 파일은 `font-license.md` 참고 |
| Pretendard(jsDelivr) | `style-src https://cdn.jsdelivr.net` · `font-src https://cdn.jsdelivr.net` |
| Firebase (Firestore/Auth) | `script-src https://www.gstatic.com` · `connect-src https://*.googleapis.com https://*.firebaseio.com wss://*.firebaseio.com` · Auth 팝업이면 `frame-src https://*.firebaseapp.com` |
| Supabase | `connect-src https://<프로젝트>.supabase.co wss://<프로젝트>.supabase.co` · 스토리지 이미지면 `img-src`에도 |
| 앱스스크립트 웹앱 API | `connect-src https://script.google.com https://script.googleusercontent.com` |
| YouTube 임베드 | `frame-src https://www.youtube-nocookie.com https://www.youtube.com` · `img-src https://i.ytimg.com` |
| 외부 이미지 URL | `img-src`에 그 도메인 (가능하면 앱 안에 파일로 두기) |
| html2canvas / 캔버스 저장 | `img-src data: blob:` (기본값에 있음) |
| 인쇄용 새 창(window.open + document.write) | 새 창이 CSP를 물려받음. 새 창 안의 글꼴·이미지도 위 규칙을 따른다 |
| 인라인 `<script>`, `onclick` | `script-src 'unsafe-inline'` (단일 HTML 앱은 대부분 필요) |

## Permissions-Policy

기본값: `camera=(self), microphone=(), geolocation=(), payment=(), usb=(), web-share=(self)`
- 카메라를 안 쓰면 `camera=()`
- 녹음을 쓰면 `microphone=(self)`
- 공유 기능이 없으면 `web-share=()`

## Netlify로 옮길 때 (`_headers`)

```
/*
  Content-Security-Policy: <같은 값>
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: <같은 값>
```

## 자주 생기는 문제

- 글꼴이 기본 글꼴로 보임 → `font-src` 누락 (외부 폰트 CSS를 부르면 `style-src`도 필요)
- 이미지 저장이 빈 이미지 → `img-src data: blob:` 누락, 또는 외부 이미지 도메인 누락
- Firebase 연결 실패 → `connect-src`의 `wss://` 누락
- 다른 사이트(패들렛, 구글 사이트 등)에 앱을 끼워 넣어 쓰는 경우 → `frame-ancestors 'none'`과 `X-Frame-Options: DENY`가 막는다. 끼워 넣을 곳이 있으면 `frame-ancestors`에 그 도메인을 넣고 `X-Frame-Options`는 뺀다.
