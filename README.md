# 홈페이지 첫 화면 — 캐릭터 스크럽 + 색 전환

아임웹 첫 섹션에 얹는 스크롤 연출. 캐릭터가 스크롤에 맞춰 돌고, 이어서 색 패널이
액체처럼 차오르며 마크가 떠오른다.

캐릭터는 아직 **임시 구 도형**이다. 실제 캐릭터가 나오면 파일만 교체한다.

---

## 파일

| 파일 | 용도 |
|---|---|
| `imweb-block.html` | **아임웹 코드 블록에 통째로 붙여넣는 것.** 히어로 + 색 전환 한 덩어리 |
| `imweb-transition.html` | 사이트 전체 스크롤 등장 효과 (선택) |
| `imweb-pagewipe.html` | 페이지 전환 효과 (현재 미사용) |
| `demo.html` | 전체 구조 로컬 미리보기 |
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

`--model` 을 빼면 임시 구 도형으로 돈다. `--pose` 는 `ball` `stand` `sit`,
`--camera move` 를 주면 오브젝트 대신 카메라가 움직인다.

렌더 후 푸시하면 CDN 이 따라간다. 아임웹 코드는 건드릴 필요가 없다.

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
| CSS `.qc-hero` | `280vh` | 캐릭터 회전에 쓰는 스크롤 길이 |
| CSS `.qc-green` | `300vh` | 색 전환에 쓰는 길이 |
| CSS `.qc-root` 상단 | 색 3개 | 배경 · 광원 · 전환색 |
| JS `lerp` | `0.1` | 관성. 낮출수록 묵직 |
| JS `waveHz` | `30` | 파형 갱신 빈도. 낮출수록 가볍다 |
| JS `startAt` | `10` | 앞쪽 이만큼 받으면 먼저 시작. 나머지는 뒤에서 채운다 |
| JS `SNAP_END` | `0.88` | 스냅 도착 지점 |

---

## 성능 메모

- 캔버스를 원본 크기로 두고 화면 맞춤은 CSS `object-fit` 에 맡긴다.
  확대 계산이 사라져 그릴 때 1:1 복사가 된다.
- 프레임은 `ImageBitmap` 으로 미리 디코딩해 둔다.
- 프레임 수와 해상도가 메모리를 지배한다. 36장 × 1000×560 ≈ 77MB.
  올리기 전에 이 값을 먼저 확인할 것.
- 파형은 30fps 로만 갱신하고, 다 덮인 뒤에는 계산을 건너뛴다.

---

## 주의

- 아임웹은 **편집 모드에서 스크롤 연출이 제대로 안 보인다.** 미리보기나 실제 주소로 확인한다.
- 첫 섹션의 좌우 여백을 0 으로 둔다.
- 조상 요소가 `overflow` 를 자르면 `sticky` 가 죽는다. 스크립트가 자동으로 풀지만,
  그래도 안 되면 섹션 설정에서 전체 너비 옵션을 켠다.
- 구성과 인터랙션 패턴만 참고했다. 캐릭터 · 카피 · 색은 전부 새로 만든다.
