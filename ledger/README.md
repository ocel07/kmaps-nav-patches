# 분류 원장 (네이버 지도·카카오맵·TMAP, GNSS 주기 의존 지점)

앱 업데이트 대응 절차 L3의 원장이다. 탐지기가 뽑은 **후보 전부**와 **우리 패치 지점 전부**를 판정과 함께 적는다.
새 버전에서 다시 돌렸을 때 규칙에 없는 후보(= 새 코드)가 `UNCLASSIFIED`로 드러나게 하는 것이 목적이다.
(아틀란 원장은 2026-11-15 상위 프로젝트 `archive/atlan/ledger/`로 보관.)

| 파일 | 내용 |
|---|---|
| `naver_rules.tsv` | 판정 규칙. 기준 6.10.0.16 |
| `naver_ledger_6.10.0.16.tsv` | 297행: PATCHED 118 · OK 70 · INACTIVE 20 · OUT 89 · 미분류 0 |
| `naver_rules_6.11.2.2.tsv` | 6.11.2.2 규칙(6.10 규칙 − 대상 없어진 정확 규칙 + 6.11 판정) |
| `naver_ledger_6.11.2.2.tsv` | 410행: PATCHED 120 · OK 78 · INACTIVE 28 · OUT 184 · 미분류 0 (패치 행은 Morphe 사이트) |
| `naver_rules_6.12.2.4.tsv` | 6.12.2.4 규칙(6.11 규칙 − STALE 4 + 6.12 판정 7: `setInterval` 이름 n1, R2 인자 추가, Compose 차선 UI 등). **다음 버전은 이 파일에서 시작** |
| `naver_ledger_6.12.2.4.tsv` | 413행: PATCHED 120 · OK 81 · INACTIVE 28 · OUT 184 · 미분류 0 |
| `kakao_scope.txt` | 카카오맵 스캔 범위(소스 파일 이름 패턴, `module:` Kotlin 모듈, `pkg:` 패키지) |
| `kakao_rules_5.17.8.tsv` | 카카오맵 5.17.8 규칙. 키가 **원래 소스 파일 이름**(아래 "카카오맵") |
| `kakao_ledger_5.17.8.tsv` | 389행: PATCHED 6 · OK 87 · INACTIVE 38 · OUT 258 · 미분류 0 |
| `kakao_rules_6.32.0.tsv` | 6.32.0 규칙(5.17.8 규칙 − STALE 62 + 6.32 재조사 판정) |
| `kakao_ledger_6.32.0.tsv` | 464행: PATCHED 7 · OK 72 · INACTIVE 35 · OUT 350 · 미분류 0 |
| `kakao_rules_6.33.0.tsv` | 6.33.0 규칙(6.32 규칙을 새 키 `syn:R8`·`<lib:…>`로 바꿈, 판정 변경 없음). **다음 버전은 이 파일에서 시작** |
| `kakao_ledger_6.33.0.tsv` | 464행: PATCHED 7 · OK 72 · INACTIVE 35 · OUT 350 · 미분류 0 (6.32와 같은 코드, R8 줄 번호만 다름) |
| `tmap_rules_11.8.4.4075.tsv` | TMAP Java 규칙(아래 "TMAP"). 판정 근거 상위 프로젝트 `docs/tmap/J_java.md` |
| `tmap_java_ledger_11.8.4.4075.tsv` | 222행: PATCHED 16 · OK 32 · INACTIVE 9 · OUT 165 · 미분류 0 |
| `tmap_native_rules_11.8.4.4075.tsv` | TMAP 네이티브 규칙: `libNavigationSDK.so`(N2) + `libtmapnavigationengine.so`(N1, 전부 INACTIVE) |
| `tmap_native_ledger_11.8.4.4075.tsv` | 120행: PATCHED 45(바이트 패치 28 + 후보 17) · OK 54 · INACTIVE 21 · 미분류 0 |

도구는 `../tools/`, 중간 산출물(후보 목록, smali 트리)은 저장소 밖에 둔다(앱 코드가 들어 있음).

## 카카오맵 (난독화 앱)

KNSDK·KM 위치 SDK는 클래스·패키지 이름이 버전마다 바뀌고(`om/b`, `jo/c`), `.source`(원래 파일 이름)만 남는다. 그래서
- `dexclasses.py --srcmap`이 dex에서 "클래스 → 소스 파일" 표를 만든다.
- `scan_smali.py --srcmap … --scope kakao_scope.txt`: 범위는 소스 이름 패턴이 맞는 클래스가 있는 **패키지 전체**(같은 패키지의 새 파일도 스캔).
  6.32.0부터 R8이 난독화 클래스를 **기본 패키지로 평탄화**(`heb`, `ieb`)해서 패키지 단위가 무의미해졌다 → 기본 패키지 클래스는 클래스 단위로 보고,
  `module:<정규식>` 줄로 Kotlin 내부 멤버 이름 접미사(`$library_release` = KM 위치 SDK, `$app_knsdk_…Release` = KNSDK)가 나오는 클래스의 소스 파일 전체를 범위에 넣는다(새 파일 이름도 잡힘). 키는
  - class = `src:KNGPSData.kt` (라이브러리 내부는 `lib:<artifact>`, 버전 번호 제외)
  - 기본 패키지로 평탄화된 클래스 중 소스 이름이 없는 것(6.33.0부터): R8 합성 클래스(`R8$$SyntheticClass`)는 `syn:R8`, 라이브러리 클래스(`lib@@ver`)는 `lib:<artifact>`·desc 안에서는 `<lib:artifact>`. 이 클래스들은 빌드마다 이름이 바뀌어서 이름 키로는 원장이 매번 흔들렸다
  - desc 안의 앱 타입 = `<KNGPSData.kt>`, TIMER/LOCREQ detail의 소유자도 같은 방식(`<Delay.kt>->delay`)
  - 난독화 클래스·메서드 이름은 정보 열(`method` = `om/b.a`)에만 남는다.
- 내비 핵심 파일은 정확한 키 규칙(같은 키의 반복 n만 `*`), UI·렌더러·DB·통신 파일과 라이브러리는 파일 단위 와일드카드.
- 패치 행: `export_patches_morphe.py --app kakao`(KakaoPatch.kt의 `src:` 사이트, ID = note 첫 단어 K1·K2·K3).
- 5.17.8 판정 근거는 상위 프로젝트 `docs/kakao/A_location.md`·`B_matching.md`·`C_guidance.md`, 설계는 `docs/kakao-rate-patch.md`.
  INACTIVE 중 다시 볼 것: 레거시 경로(서버 `positioning_opt` 1·2), 실내 판정(`InOutCheckerV2` 등, 서버 indoor), GPS 로그 업로드(서버 `gpslog`).

```bash
# 카카오맵 <ver>: W = 저장소 밖 작업 폴더. decompile.py = dex 전부 baksmali + srcmap.tsv + grep용 idx/
python tools/decompile.py <base.apk> $W
python tools/scan_smali.py --root $W/smali --srcmap $W/srcmap.tsv --scope ledger/kakao_scope.txt --locreq-all --out $W/hits_<ver>.tsv
python tools/export_patches_morphe.py --app kakao --out $W/patches_<ver>.tsv
python tools/ledger.py --hits $W/hits_<ver>.tsv --hits $W/patches_<ver>.tsv --rules ledger/kakao_rules_<ver>.tsv --out ledger/kakao_ledger_<ver>.tsv --strict
```
- 탐지기 시험(11-15): 가짜 새 카운터(KNGuidance.kt) 1건 → `UNCLASSIFIED` + `--strict` 종료 코드 1. 스캐너를 바꾼 뒤 네이버 6.10.0.16 결과(136행)가 그대로인 것도 확인.
- 탐지 패턴 보강(11-15): 난독화된 코루틴 `delay`(`kotlinx/coroutines/a1;->delay`)·Flow `sample/debounce`, 소유자가 난독화된 `->requestLocationUpdates`, `LocationRequest$a`(Builder).
- 기계 탐지가 못 잡는 지점(상수 비교, 레지스터 비교: B 문서 M-01·M-02·M-11·M-17, A6·A12)은 문서 판정과 패치 행으로 관리한다.

## TMAP (Java + 네이티브 엔진)

TMAP은 원장이 둘이다. Java(위치 공급·필터·큐, `TmapPatch.kt` J1~J7)와 네이티브 엔진(`libNavigationSDK.so` 바이트 패치 N2, 새 엔진 `libtmapnavigationengine.so`).

**Java 키**: 엔진 SDK `com/skt/tmap/engine/navigation/**`는 클래스 이름이 남고 `.source`가 `SourceFile`로 지워져 있어 **클래스 경로**가 키다.
앱 패키지의 난독화 클래스(`com/skt/tmap/location/m`, `engine/i$c` 등)는 원래 소스 이름이 남아 있어 `--srcmap`으로 **`src:TmapNaviLocationManager.java`** 가 키가 된다(카카오맵과 같은 방식, `TmapPatch.kt` J2도 `src:`).
즉 한 번의 `--srcmap` 스캔에서 이름이 남은 클래스는 경로, 난독화된 것은 소스 파일 이름으로 자동으로 갈린다. R8 합성 클래스(`R8$$SyntheticClass`)만 경로가 남는다(아직 후보 없음).
- 스캔 범위 `--pkg com/skt/tmap/engine,com/tmapmobility/tmap/tmapnavigationengine,com/skt/tmap/location` + `--locreq-all`.
- 미패치로 남긴 J13~J18(표본 창, 낮음)은 `OK` + reason "미패치(낮음)"로 적었다. 패치하면 `PATCHED`로 바꾼다.
- 범위 밖 와일드카드: GMS(`lib:`), 도보·대중교통, AI 안경, 도착 알림, A.(adot), MoEngage, Wi-Fi 에이전트, 위치 리포트 서비스, `engine/navigation/network/**`, `jamming/**`(J27 통계).

**네이티브 키**: `kind` · `<lib>:<demangle 함수 이름>`(같은 이름이 둘 이상이면 인자 목록까지) · 멤버 오프셋(`+0xac`)/전역(`global` 또는 이름 있는 심볼 `g:…`)/상수(`int1000`, `f3.6`) · 세부(`+1`, `+r`, `inc`, `cmp #4`, `fmul`…) · `n`.
주소는 `addr` 정보 열에만 있다(빌드마다 바뀜). 이름 없는 함수는 처음 닿은 이름 있는 호출자로 `sub<CMmCacheV2::GetCacheCopyData(uint)>`처럼 적는다.
`PATCH` 행은 `navsdk_<ver>.json` 항목마다 한 행: class = 패치 주소를 품은 함수(ELF 헤더 항목은 `NavigationSDK:ELF`), desc = 항목 ID(W, N2-1…, CAVE, SLOT), detail = 원래 명령(분기 대상은 `L`).
새 엔진은 숨은 개발자 설정 `DATA_USE_PROTOBUF_RP`(기본 꺼짐)에서만 쓰이므로 후보를 정확한 키로 다 적되 판정은 `INACTIVE`, ref = N1 항목(E1~E16). 기본값이 바뀌면 N1 문서의 패치 지점과 함께 다시 판정한다.

`tools/scan_native_ida.py`(IDAPython, IDA 9, ARM64): 도달 집합 = 진입점에서 BL/꼬리 B로 호출 깊이 6까지(PLT 썽크는 실제 함수로 풀고, `std::`·`__`·`SDL_` 등 라이브러리 함수 안으로는 내려가지 않음).
진입점: navsdk = `nativeInputLocationData` → `CNaviController::InputLocationData` → `CNaviModule::ReceiveGps`/`MapMatch`, `GetRouteGuidance` 경로, vtable로만 불리는 `NcRouteMatchEX::SetGpsParsedData/MapMatching`·`NcLocalMatch`·`NcBaseMatch::AddGpaData`·`CRGPlayer::GetDriveInfo`·`SectionSpeedMonitor::Update`·`SpeedCalculator::Update`(목록은 스크립트 `TARGETS`).
engine = JNI `putLocation` → `MapMatch::PutLocation`/`GetMapMatchResult`, `RouteGuidanceResult::GetDriveInfo`, `RouteGuidanceVoice::MakeVoiceService`/`SDIService`, `DangerAreaInfomation::GetDAInfo`.
- `COUNTER`: `LDR w,[m]` → `ADD/SUB #k`(1~16)·`ADD reg`·`CINC/CSINC` → 같은 `[m]`에 `STR`(무조건 B는 따라가고 조건 분기는 통과). 스택은 제외.
- `CTRCMP`: 그 값이나 같은 클래스 멤버/전역을 도달 집합 어디서든 읽어 즉시값 ≥ 2와 비교.
- `ONE_SEC`: 정수 1000(MUL/DIV/CMP/호출 인자/저장에 쓰임), 실수 상수 1000·0.001·3.6·1/3.6·3600을 쓰는 FMUL/FDIV(ms↔s, km/h↔1 s 이동거리).

```bash
# TMAP <ver>: W = 저장소 밖 작업 폴더(probe_out/tmap/work/<ver>), L = probe_out/tmap/lib
# 1) Java
python -I tools/decompile.py <base.apk> $W
python -I tools/scan_smali.py --root $W/smali --srcmap $W/srcmap.tsv --pkg com/skt/tmap/engine,com/tmapmobility/tmap/tmapnavigationengine,com/skt/tmap/location --locreq-all --out $W/hits_<ver>.tsv
python -I tools/export_patches_morphe.py --app tmap --out $W/patches_<ver>.tsv          # TmapPatch.kt TMAP_SITES, ID = note 첫 단어 J1..J7
python -I tools/ledger.py --hits $W/hits_<ver>.tsv --hits $W/patches_<ver>.tsv --rules ledger/tmap_rules_<ver>.tsv --out ledger/tmap_java_ledger_<ver>.tsv --strict
# 2) 네이티브: split_config.arm64_v8a.apk의 lib/arm64-v8a/*.so 원본(패치 전)을 IDA로 분석해 둔 DB($L/*.so.i64)에서
#    IDA MCP(open_database → execute_python) 또는 IDA 안 Python 창:
#      g = {}; exec(open(r'tools/scan_native_ida.py', encoding='utf-8').read(), g)
#      g['main'](r'$W/native_navsdk_<ver>.tsv', 'navsdk', r'tools/tmap/navsdk_<ver>.json')   # libNavigationSDK.so.i64 + PATCH 행
#      g['main'](r'$W/native_engine_<ver>.tsv', 'engine')                                 # libtmapnavigationengine.so.i64
#    → 반환 문자열에 도달 함수 수·행 수·못 찾은 진입점(missing roots)이 나온다. missing이 있으면 TARGETS를 고친다.
python -I tools/ledger.py --hits $W/native_navsdk_<ver>.tsv --hits $W/native_engine_<ver>.tsv --rules ledger/tmap_native_rules_<ver>.tsv --out ledger/tmap_native_ledger_<ver>.tsv --strict
```
- 새 버전은 직전 버전 규칙 두 파일을 복사해 시작한다. `.so` 해시가 바뀌면 바이트 패치 목록부터 다시 만들어야 하므로(`tools/tmap/src`, NAV_PATCH_RESUME 6절) 네이티브 `PATCH` 행은 새 JSON으로 다시 낸다. `detail`이 `?orig-mismatch`로 시작하면 JSON의 원래 바이트가 DB와 다르다(패치본 DB를 열었거나 JSON이 다른 빌드용).
- 11.8.4.4075 결과: navsdk 도달 574함수·후보 72행, engine 도달 203함수·후보 20행. N2 문서의 카운터(N2-2 +0xAC, N2-3 +0x988, N2-4 +0x4D0, N2-5 +0x7CC/+0x7D0, N2-7 +0x320·전역, N2-10 +0x3E0, N2-1 `MOV W3,#1000`)와 N1의 E1~E3(+0x61C, +0x618)을 모두 잡았다.

한계(네이티브 탐지기):
- 간접 호출(BLR, vtable)은 따라가지 않는다 → vtable 메서드는 진입점 목록에 직접 넣는다. 새 가상 메서드가 생기면 놓칠 수 있다.
- 레지스터끼리 비교하는 임계(N2-10의 `this+0x3F0`=210, N2-1 램프 `CMP W9,#0xA`처럼 카운터가 아닌 값의 비교), 거리 절삭(N2-4·N2-5의 `FCVTZS`+`CMP #9/#2`)은 후보 종류에 없다 → 문서 판정과 `PATCH` 행으로 관리한다.
- 카운터 추적은 직선 경로 14명령까지라 저장이 멀리 떨어지거나 메모리 대신 레지스터에 오래 머무는 카운터는 놓친다. 루프 지역 변수(스택)는 일부러 뺐다.
- 이름 없는 함수의 키는 호출자 이름에 기대므로 호출 구조가 바뀌면 키가 바뀐다(STALE + UNCLASSIFIED로 드러남).
- `vsm_log_*`·`__android_log_print` 같은 fix당 비용(N2-9)은 후보 종류가 아니다.

## 판정

| 값 | 뜻 |
|---|---|
| `PATCHED` | 우리 패치가 처리한다. `ref` = 패치 ID(R/M/L/T/S/V/F/A/P/G, `guide-*`, `N1`, `M9`; 카카오 K*; TMAP J*·N2-*·W·CAVE·SLOT) |
| `OK` | 주기와 무관(시간 기준, 공간 기준, 목록 길이, 로그 전용 등). 근거는 `reason` |
| `INACTIVE` | 이 기기·현재 설정에서 안 도는 경로(AVN/CarPlay/듀얼 GPS, 모의주행, 디버그 등). 설정을 바꾸면 재검토 |
| `OUT` | 차량 내비 범위 밖(도보 내비, 위치 공유, 외부 라이브러리·SDK) |

## 키 (버전이 바뀌어도 흔들리지 않게)

- `kind` · 클래스 · **메서드 디스크립터(이름 제외)** · 세부(필드 타입±1, 상수, API) · `n`(같은 키 안의 순번). R8이 메서드·필드 이름을 바꿔도 키는 그대로다. 메서드 이름은 정보 열에만 있다.
- `PATCH` 행: 패치 지점(클래스·메서드 지정·앵커 첫 줄).
- 규칙의 `*`는 아무 값, 클래스 `pkg/**`는 패키지, `pkg/Cls**`는 클래스와 내부 클래스. 가장 구체적인 규칙이 이긴다.
  **차량 내비 코드는 전부 정확한 키 규칙**이고, 와일드카드는 범위 밖(도보, 외부 라이브러리)과 `PATCH` 행에만 쓴다. 그래야 새 코드가 규칙에 묻히지 않는다.

## 다시 만들기

```bash
# 분해 → 후보 → 패치 지점 → 원장  (W = 저장소 밖 작업 폴더)
python tools/dexclasses.py <base.apk> --pkg Lcom/naver/maps/navi/,Lcom/naver/map/core/navigation/ --count   # 내비 클래스가 든 dex
python tools/dexclasses.py <base.apk> "--refs=->requestLocationUpdates,gms/location/LocationRequest;->"     # 위치 요청 API를 참조하는 dex
#   위 dex들을 baksmali(--debug-info false)로 $W/smali/classesN/ 아래에 푼다
python tools/scan_smali.py --root $W/smali --pkg com/naver/maps/navi,com/naver/map/core/navigation --locreq-all --out $W/hits_<ver>.tsv
python tools/export_patches_morphe.py --out $W/patches_<ver>.tsv          # NaverSites.kt + NaverPatch.kt 손작성 지점
python tools/ledger.py --hits $W/hits_<ver>.tsv --hits $W/patches_<ver>.tsv --rules ledger/naver_rules_<ver>.tsv --out ledger/naver_ledger_<ver>.tsv --strict
```

- `UNCLASSIFIED`: 코드를 보고 판정한 뒤 규칙을 추가한다(고쳐야 하면 `NaverSites.kt`/`NaverPatch.kt`에도). 0이 될 때까지 빌드를 내보내지 않는다.
- `STALE rule`: 규칙이 아무것도 못 맞췄다 → 코드가 없어졌거나 키가 바뀌었다. 같은 코드를 찾아 규칙 키를 고친다.
- `export_patches_morphe.py`의 `HAND` 목록은 `NaverPatch.kt` 손작성 지점과 맞춰 둔다(새 손작성 지점을 넣으면 같이 추가). 6.11.2.2 원장을 그대로 재현하는 것을 확인했다(11-15).
- `export_patches_naver.py`는 6.10.0.16 원장용(예전 텍스트 패치 기준). 패치 ID 표(`ID`)는 두 도구가 같이 쓴다.
- 탐지기 시험(10-11): 가짜 새 카운터 1건 → `UNCLASSIFIED` + `--strict` 종료 코드 1, 메서드 이름만 바꾼 행 → 그대로 판정됨.

## 확인해 둔 것

- 네이버 내비 클래스는 맵매칭·안내·NaviStore 외에 설정·로그·인증, 도보 시뮬레이션 dex에도 있다. 6.10·6.11 모두 스캔했다.
- 위치 요청 API를 쓰는 곳 중 내비 입력은 `FusedLocationSource`·`SystemLocationSource`(N1)뿐이다. 나머지는 Android Auto QA 화면, 광고 SDK, androidx, 위치 기록 디버그, 위치 공유, Clova SDK, Play 서비스 내부.
- 탐지기 한계: 패턴 밖의 1초 전제(예: `floor(경과초)`를 표본 수로 쓰는 코드는 `FLOOR`로 일부만 잡힘)는 놓칠 수 있다. 그래서 버전 diff·실행 확인과 함께 쓴다.
