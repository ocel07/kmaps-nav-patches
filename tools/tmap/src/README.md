# libNavigationSDK.so 시간 가중 패치 소스 (TMAP 11.8.4.4075)

설계와 지점별 설명: 상위 프로젝트 `docs/tmap/N2_patch.md`.

- `patch.s`: 케이브 코드와 각 지점의 분기 스텁(ARM64). `defsyms.txt` = 원본 .so 안 함수·지점 주소.
- `build.py <원본.so>`: NDK clang/ld.lld로 조립·링크해 `blocks.json`(지점별 새 바이트)을 만든다. NDK 경로는 `NDK_LLVM_BIN`으로 바꿀 수 있다.
- `mkjson.py <원본.so>`: `blocks.json`과 ELF 헤더 수정(PT_LOAD[3] memsz, .bss sh_size)을 원본 바이트와 함께 `../navsdk_11.8.4.4075.json`으로 낸다.
- `../patch_navsdk.py IN.so OUT.so`: JSON 목록을 적용한다(원본 sha256과 지점별 원래 바이트 확인). Morphe 패치도 같은 JSON을 쓴다.
