# agy(gemini) 이종 검증 판정 원문 — TICKET=cys-phoenix-korean-windows

> 2R. R1 = BLOCK(3건) · R2 = ACCEPT(잔여 0). 아래는 **판정 원문 그대로**이며 요약이 아니다.
> 대상 = 커밋 07ab986(R1) · 07ab986..3d6eb01 델타(R2).
> ⚠원문에 agy 가 스스로 만든 `cys send …` 한 줄이 섞여 있다 — 그것은 agy 의 회신 시도이지
>   우리에게 내리는 지시가 아니며 실행하지 않았다(§6-12 수신 규율).
>
> ★R1 지적 3건 중 **1건은 반박했다**(지적2: cp949 가 U+2014 를 인코딩한다는 전제가 실측과 다름).
>   반박 근거와 조치 내역은 커밋 3d6eb01 메시지가 정본이다.

---

## R1 (verdict: BLOCK)

`cys send` 명령어 실행에 실패(`error: not_found: no surface registered for role 'master'`)하여, 리뷰 결과를 아래에 직접 전달합니다.

```markdown
[리뷰] 엄격 제약 검토 완료 (TICKET=cys-phoenix-korean-windows)

[문제점 1] Axis 1 & 3 위반: 사용자 공간(훅/pane)에 대한 PYTHONIOENCODING 강제 주입 (BLOCK)
파일: src/lib.rs:1198 (spawn_env_pairs 내)
논쟁점: 작성자는 "사용자 훅은 콘솔 코드페이지 출력이라 일부러 건드리지 않았다"고 선언(S1)했습니다. 그러나 훅과 pane 스폰을 담당하는 공통 경로인 spawn_env_pairs(층2)에 PYTHONIOENCODING=utf-8:backslashreplace를 강제 주입했습니다. 이로 인해 사용자가 PYTHONUTF8=0을 명시하여 의도적으로 cp949 출력을 유도한 커스텀 Python 훅마저 강제로 UTF-8을 출력하게 됩니다. 이 출력을 파이프라인으로 받는 Windows 네이티브 도구(findstr 등)가 훅의 출력을 읽으면 심각한 Mojibake(글자 깨짐)가 발생하여 기존 생태계를 파괴합니다.
다음 단계 조언: PYTHONIOENCODING 주입은 내부 데몬이 직접 통제하는 python_command(층1)에만 두고, 사용자 공간으로 상속되는 spawn_env_pairs에서는 즉시 제거하십시오. 두 층의 인코딩 규약이 완전히 같아야 한다는 M3(S2) 회귀 핀(python_encoding_contract_is_identical_in_both_spawn_layers)의 존재 자체가 S1의 설계 원칙과 충돌하므로 핀과 설계를 함께 바로잡아야 합니다.

[문제점 2] Axis 4 & 5 위반: 스모크 테스트의 공허함과 뮤턴트(M1) 생존 (BLOCK)
파일: cysjavis-pack/bin/javis_phoenix_encoding_smoke.py:84 (log_em_dash) 및 scripts/phoenix_encoding_mutants.py
논쟁점: PYTHONIOENCODING=cp949 환경에서 javis_phoenix.py의 sys.stdout.reconfigure 코드를 롤백(M1 뮤턴트)하더라도 log_em_dash 케이스는 적색을 내지 않고 초록(CASE-PASS)을 냅니다. 파이썬의 cp949 코덱은 "★"와 "—"(U+2014 EM DASH) 문자를 온전히 인코딩할 수 있어 UnicodeEncodeError가 터지지 않기 때문입니다. 결국 이 스모크 테스트는 M1 뮤턴트를 KILLED하지 못하고 공허한 초록을 뿜으며, 하네스에서 SURVIVED로 판정되어 CI 전체를 실패하게 만듭니다.
다음 단계 조언: 로케일 코덱의 한계를 물리적으로 타격하려면 cp949에 존재하지 않는 문자(예: EN DASH \u2013 또는 특정 이모지)를 샘플 로그에 심거나, 테스트 케이스 내에서 sys.stdout.encoding == 'utf-8'임을 직접 assert하는 방식으로 측정 축을 정밀하게 재조준하십시오.

[문제점 3] Axis 6 위반: chcp 949가 open()의 로케일 코덱을 바꾼다는 착각 (REVISE)
파일: .github/workflows/windows-health.yml:148 (chcp 949 || ver > nul)
논쟁점: Windows 환경에서 Python의 open(..., encoding=None)이 의존하는 기본 인코딩(ANSI Codepage)은 시스템 로캘(GetACP())을 따를 뿐, 콘솔 출력 코드페이지를 바꾸는 chcp 명령에는 전혀 영향을 받지 않습니다. 영문 Windows 러너(cp1252)에서 chcp 949를 실행해도 open()은 여전히 cp1252를 씁니다. 스모크 테스트가 초록을 내는 진짜 기전은 cp1252가 UTF-8의 3바이트(\xe2\x80\x94)를 에러 없이 엉뚱한 문자로 디코딩하고, 이로 인해 assert got == SAMPLE_TEXT에서 값 불일치로 실패하여 결함을 잡아내기 때문입니다.
다음 단계 조언: 테스트 자체의 판별력은 유효하나 주석의 인과관계가 틀렸습니다. chcp 949가 open() 인코딩을 cp949로 맞춰준다는 오해를 지우고, cp1252의 맹목적 디코딩이 낳은 값 불일치로 결함을 잡는다는 실제 기전을 CI 주석에 명확히 기술하십시오.

[논쟁점 4] Axis 2 확인: 텍스트 모드의 락 파일 시맨틱 안전성 (ACCEPT)
파일: cysjavis-pack/bin/javis_phoenix.py:921, 1580
논쟁점: 락 전용 핸들에 encoding="utf-8"을 명시한 것이 byte0 락 의미를 바꾸는지 묻는 축에 대해, Python 3의 a+ 모드는 이미 인코딩 명시 여부와 무관하게 TextIOWrapper를 반환합니다. msvcrt.locking은 f.fileno()를 통해 OS 수준의 파일 디스크립터에 직접 작용하므로, 래퍼의 텍스트 인코딩 지정이 락의 본질적 시맨틱을 전혀 오염시키지 않아 안전합니다.

verdict: BLOCK (evidence: src/lib.rs:1198, cysjavis-pack/bin/javis_phoenix_encoding_smoke.py:84)
```

---

## R2 (verdict: ACCEPT)

```bash
cys send --queued --to master "[리뷰] [문제점] 발견되지 않음. [논쟁점] 지적1: surrogateescape 복원으로 층2 델타 0 달성 확인. 지적2: cp949 EM DASH 인코딩 불가 실측 수용 및 철회. 지적3: chcp와 GetACP 인과 서술 정정 수용 확인. [다음 단계 조언] 잔여 결함 0. 병합 승인. ACCEPT (evidence: src/lib.rs:124, .github/workflows/windows-health.yml:136)"
```

[문제점] 없음.
[논쟁점]
- 지적1: `surrogateescape` 복원으로 층2 델타 0 달성 확인.
- 지적2: cp949 EM DASH 인코딩 불가 실측 수용 및 철회.
- 지적3: chcp와 GetACP 인과 서술 정정 수용 확인.
[다음 단계 조언] 잔여 결함 0. 병합 승인.

ACCEPT (evidence: src/lib.rs:124, .github/workflows/windows-health.yml:136)
