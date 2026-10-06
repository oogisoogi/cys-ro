# R 의식 — 폐기문 서명 절차 (1쪽 · 1.1.8 U3)

> 설계 정본 = `DESIGN-AUTOUPDATE-118.md` §4-1(키 체계 R 행) · §4-6(위협 표 「키 유출」) · §9 R9.
> 서식 정본 = U1 `src/update/keys.rs`(`RawRevocations` · `kind="update-revocations"` · 위임 `pubkey` 필수 · 폐기 릴리스 `component` 필수).
> **사건 때만** 한다(정기 0). 실행 = master · 매체 꽂기·빼기 = 박사님 손 1단계.

## 언제 하는가 (이 넷 말고는 하지 않는다)
| 사건 | 이번 폐기문에 넣는 것 | 명령 칸 |
|---|---|---|
| U·F·A2 키 교체(유출 의심·만료 전 교체) | 새 키 **위임** + 옛 키 **폐기** | `--delegate <purpose>:<새.pub>:<not_after 정수 초>` · `--revoke-key <옛 key id>` |
| 특정 릴리스가 나쁘다 | 그 릴리스 **무효화** | `--revoke-release <component>:<seq>:<advisory\|stop_seats>:<reason_code>` |
| 맥 서명 인증서 교체(R4 · cys-local 만료 2027-08-13 전) | 새 **DR 핀 추가**(먼저) → 다음 판에서 옛 핀 **폐기** | `--dr-pin-add <40 hex>` · `--dr-pin-revoke <40 hex>` |
| A2(윈 자산 키) 교체 | A2 위임 + 발행 게이트 7-b 상수 갱신 | `--delegate win-asset:…` + `scripts/release-verify.py` `A2_KEY_ID` = `scripts/update/update_common.py` `A2_KEY_ID`(같은 커밋 · 시험 핀이 대조) |

- **U·F·A2 키 갱신 = 만료(`not_after`) 90일 전**(결정 ③: U·F·A2 2028-01-01 → 2027-10-03 까지 · R 2036-01-01 → 2035-10-03 까지 = 새 바이너리) — 위 표 첫 행(새 키 위임 + 옛 키 폐기)을 R 서명으로 낸다. 잊으면 그날 전 기기 갱신이 「만료된 키」로 멈춘다(daily 칸).
- `stop_seats` 는 「그 판의 새 좌석 기동을 막는다」 — 기기가 사람 손 없이 멈추는 무거운 결정이다(📌17). 기본은 `advisory`.
- **R 자신은 폐기문으로 바꿀 수 없다**(도구가 거부) — R 교체 = 새 바이너리(공개키 내장) = 링크 재설치(위험 R9).
- 위임으로 루트·팩 용도는 만들 수 없다(도구 거부 · U1 검증기도 거부).

## 순서 (각 단계 실패 = 그 자리에서 멈춤 · 산출물 0)
1. **직전 폐기문을 받는다**: `curl -fsS https://jarvis.godmeyou.kr/update/revocations.json -o prev.json`(첫 폐기문이면 없음).
2. **본문을 만든다(서명 없음 · 빌드 기기)**:
   `python3 scripts/update/make-revocations.py --key-id <R key id> --prev prev.json <위 표의 칸들> --out revocations.json`
   (첫 폐기문 = `--prev` 대신 `--first` · rev = 직전 + 1 자동 · 직전에 있던 위임·폐기는 그대로 이어진다 — 빼는 것은 `--drop-delegation` 로만)
   ★2판: `--prev` 는 **같은 자리에 `prev.json.minisig` 가 있어야** 하고(1 에서 함께 받는다: `curl -fsS …/revocations.json.minisig -o prev.json.minisig`) 키링(`--keyring`, 기본 = 저장소 키링) root 키로 **암호 검증**한 것만 받는다 · 폐기 집합은 줄일 수 없다 · signed_at = 신뢰 시각(HTTPS Date 대조 · 오프라인 기기에서는 거부).
3. **박사님이 R 매체를 꽂는다**(서로 다른 장소의 두 벌 중 하나 · 📌11).
4. **서명한다**: `scripts/update/sign-revocations.sh --doc revocations.json --media /Volumes/<R 매체> --key /Volumes/<R 매체>/r.key --out-dir dist/update`
   — 스크립트가 강제하는 것: 키 경로가 매체 마운트(빌드 기기와 다른 장치) 아래가 아니면 거부 · 키를 읽지도 복사하지도 않음 ·
   폐기문만 매체로 옮겨 그 자리에서 `minisign -S` · 서명만 꺼냄 · **매체를 뺄 때까지 기다림**(최대 300초) ·
   뺀 뒤 내장 R 공개키(키링 `purpose=root`)로 검증해야 `dist/update/revocations.json(.minisig)` 이 생긴다.
5. **박사님이 매체를 뺀다**(4 의 안내 문구가 뜨면).
6. **게시 준비**: `release-gate.py revocations --doc dist/update/revocations.json --keyring cysjavis-pack/trusted-keys.json --prev prev.json --stamp`(통과 증표) → 7 의 검증 뒤 8.
   (게시기는 증표 + 재검증 · 새 rev ≤ 게시본 rev 이면 거부 · 같은 바이트면 멱등)
7. **검증 1회**(게시 전): 지금 게시된 봉투 하나로 `scripts/update/release-gate.py verify --cys <출시 cys> … --revocations dist/update/revocations.json …`
   — 무효화한 판이 설치판이면 판정이 `installed_revoked` 로 바뀌는지까지 본다(`--installed-release-seq <그 seq> --expect installed_revoked`).
8. **게시** = `python3 scripts/update/publish-site.py revocations --r2 <버킷> --file dist/update/revocations.json --live-check https://jarvis.godmeyou.kr`(R2 + `/update/*` 전용 워커 · 결정 ① · 라이브 본문·서명 sha256 대조까지 · 외부 발행 · master).

## 하지 말 것
- R 개인키 파일을 빌드 기기·클라우드·클립보드로 옮기기(스크립트가 막는 것은 경로뿐 — 사람의 복사는 못 막는다).
- 같은 rev 를 다른 내용으로 다시 내기(기기들은 rev 후퇴·동일 rev 다른 바이트를 거부/무시한다 — 늘 rev +1).
- 폐기문을 봉투 재서명(CI F)과 섞기 — 폐기문은 CI 가 만들지 않는다(F 는 R 권한 0).
