# 홈페이지 첫 화면 — 캐릭터 루프 + 붓칠 전환

아임웹 첫 섹션에 얹는 스크롤 연출. 레퍼런스는 https://theqream.com/ 첫 화면이다.
보라 배경에서 캐릭터가 계속 돌고, 스크롤을 시작하면 녹색 붓칠이 0.6초 만에 화면을 덮는다.
녹색 위에는 마크가 화면 중앙에 고정되고, 헤드라인과 서비스 목록이 그 위로 지나간다.
녹색은 반원 아치로 끝나고 둘레에 원형 텍스트가 돈다.

레퍼런스 실측값과 결정 이유는 `context-notes.md` 에 있다.

캐릭터는 아직 **임시 구 도형**이다. 실제 캐릭터가 나오면 파일만 교체한다.

---

## 파일

| 파일 | 용도 |
|---|---|
| `imweb-block.html` | **아임웹 코드 블록에 통째로 붙여넣는 것.** 히어로 · 붓칠 전환 · 녹색 · 아치 한 덩어리 |
| `imweb-transition.html` | 사이트 전체 스크롤 등장 효과 (선택) |
| `imweb-pagewipe.html` | 페이지 전환 효과 (현재 미사용) |
| `demo.html` | 전체 구조 로컬 미리보기. 첫 화면은 `imweb-block.html` 을 그대로 불러온다(복사본 없음) |
| `test-local.html` | 시퀀스만 확인하는 최소 페이지 |
| `serve.js` | 로컬 정적 서버 |
| `blender/turntable.py` | 캐릭터 렌더 스크립트 |
| `char/` | 캐릭터 시퀀스 · 정지 컷 · 실루엣 |

---

## 다른 컴퓨터에서 이어받기

```bash
git clone https://github.com/jkjkjkjkjk72-ux/char-assets.git
cd char-assets
node serve.js
```

브라우저에서 `http://localhost:8787/demo.html` 을 연다. Node 만 있으면 된다.

`?fast=1` 을 붙이면 관성이 꺼진다. 특정 지점 화면을 확인할 때 쓴다.

---

## 캐릭터 교체

블렌더가 필요하다 (무료). 설치 후 `.glb` 모델을 준비한다.

```bash
blender -b -P blender/turntable.py -- \
  --model "캐릭터.glb" --out "char/pc" \
  --frames 36 --width 1000 --height 560 --zoom 3.5

blender -b -P blender/turntable.py -- \
  --model "캐릭터.glb" --out "char/mobile" \
  --frames 22 --width 560 --height 1000 --zoom 3.5

blender -b -P blender/turntable.py -- \
  --model "캐릭터.glb" --out "char" --prefix "still_" \
  --still true --width 1000 --height 560 --zoom 3.5

blender -b -P blender/turntable.py -- \
  --model "캐릭터.glb" --out "char" --prefix "silhouette_" \
  --silhouette true --still true --width 1000 --height 1000 --zoom 3.2
```

루프가 끊기지 않으려면 `--angle` 을 360·(장 수-1)/장 수 로 준다(36장이면 350, 22장이면 343.6364).
지금 임시 구는 `--pose ball` 로 렌더했다.

`--model` 을 빼면 임시 구 도형으로 돈다. `--pose` 는 `ball` `stand` `sit`,
`--camera move` 를 주면 오브젝트 대신 카메라가 움직인다.

렌더 후 푸시하고, `imweb-block.html` 의 캐릭터 주소 3곳에 있는 커밋 해시를 새 해시로 바꾼다.
`@main` 은 jsDelivr 캐시가 최대 하루 늦어 옛 렌더가 섞이므로 해시로 고정한다.

```bash
git add -A && git commit -m "캐릭터 교체" && git push
```

CDN 캐시 때문에 반영이 몇 분에서 하루까지 늦을 수 있다. 급하면 주소의
`@main` 을 커밋 해시로 바꾼다.

---

## 조절값

`imweb-block.html` 안에 있다.

| 위치 | 값 | 뜻 |
|---|---|---|
| CSS `.qc-root` 상단 | 색 3개 | 히어로 바탕 · 광원 · 녹색 |
| JS `loopSec` | `3.2` | 캐릭터 한 바퀴 시간(초). 스크롤과 무관하게 돈다 |
| JS `wipeAt` | `20` | 이만큼(px) 내려가면 붓칠 시작 |
| JS `unwipeAt` | `4` | 이 위로 올라오면 붓칠을 걷는다 |
| JS `startAt` | `10` | 앞쪽 이만큼 받으면 먼저 시작. 나머지는 뒤에서 채운다 |
| CSS `.qc-band` | `.58s` | 붓칠 속도 |
| CSS `.qc-spin` | `60s` | 링 텍스트 한 바퀴. 아치 텍스트는 스크롤 1px 당 0.107도 |
| HTML `.qc-graf` | 보라 붓 획 | 그래피티 배경 자리. 이미지가 나오면 img 로 바꾼다 |
| JS `mark` | 마스몬스터 로고 | 녹색 위 마크. 3D 마크 영상이 나오면 교체 |

---

## 성능 메모

- 캔버스를 원본 크기로 두고 화면 맞춤은 CSS `object-fit` 에 맡긴다.
  확대 계산이 사라져 그릴 때 1:1 복사가 된다.
- 프레임은 `ImageBitmap` 으로 미리 디코딩해 둔다.
- 프레임 수와 해상도가 메모리를 지배한다. 36장 × 1000×560 ≈ 77MB.
  올리기 전에 이 값을 먼저 확인할 것.
- 캐릭터 루프는 녹색에 덮인 뒤에는 그리지 않는다.
- 붓칠은 SVG 마스크 안의 transform 만 바꾼다. 0.6초 동안만 그리고 끝나면 정지 화면이다.
- 링·아치 텍스트는 svg 가 아니라 감싼 div 를 돌린다. svg 를 직접 돌리면 크롬이 글자 경로를
  매 프레임 다시 배치·페인트한다(실측 프레임당 약 2ms). 안 보일 때는 회전을 멈춘다.
- 실측(CPU 4배 감속): 스크롤 중 스크립트 약 2ms, 페인트 0ms, 60fps 유지.

---

## 주의

- 아임웹은 **편집 모드에서 스크롤 연출이 제대로 안 보인다.** 미리보기나 실제 주소로 확인한다.
- 첫 섹션의 좌우 여백을 0 으로 둔다.
- 조상 요소가 `overflow` 를 자르면 `sticky` 가 죽는다. 스크립트가 자동으로 풀지만,
  그래도 안 되면 섹션 설정에서 전체 너비 옵션을 켠다.
- 구성과 인터랙션 패턴만 참고했다. 캐릭터 · 카피 · 색은 전부 새로 만든다.
- 아임웹은 1920px 디자인을 body zoom 으로 줄인다(1440 화면에서 0.74). 블록은 역배율 zoom 을 걸어 실제 크기로 되돌리고,
  고정 헤더 높이를 재서 그만큼 고정 화면을 내린다.
- 스크롤 위치는 `getBoundingClientRect` 로 잰다. `offsetTop` 은 부모 기준이라
  블록 위에 헤더나 다른 섹션이 있으면 어긋난다(실제로 겪은 버그).
- 레퍼런스의 3D 영상·그래피티·붓칠 Lottie 는 그쪽 자산이라 가져오지 않았다. 구조와 타이밍만 따랐다.
