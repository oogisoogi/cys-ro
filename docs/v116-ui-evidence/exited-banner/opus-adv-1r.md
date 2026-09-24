# opus 적대 서브에이전트 1R — 대상 802ca149(3bc73856..) 제품 diff · 판정 ACCEPT(MAJOR 0 · MINOR 2 · NIT 4)
(원문 요지 · xterm 5.5.0 소스 대조 = 서브에이전트가 ui/node_modules/@xterm/xterm/src 를 직접 읽음)

확인(성립): 쓰기 순서(WriteBuffer._innerWrite 안 콜백 → 같은 대기열 끝) · carry 미완 CSI 는 reset 의 ESC 로 취소 · ESC[r = 활성 버퍼 여백만·커서 원점 · 주 화면 마지막 행 스크롤 = 스크롤백 편입(5000 상한은 평소 출력과 같음) · 같은 term 스트림 재시작 없음(start_surface_stream 은 makePane 에서만 · Rust 종료 이벤트 1회).

MINOR-1 대체 화면이 마지막 행까지 차 있으면(Claude Code 전체 화면 상태 줄 · vim 상태 줄) 앞·뒤 줄바꿈 2회로 윗줄 2개 영구 손실(대체 화면엔 스크롤백 없음) · 헤드리스 ⒝는 30줄뿐이라 못 잡음. 권고: 마지막 행이면 뒤 줄바꿈 빼기 등.
MINOR-2 가짜 터미널이 위험 의미를 모형화 못함(콜백 안 쓰기의 같은 패스 · trimRight 인자 무시) · 대체 화면 가득·배경색 빈 줄·판독~해석 사이 리사이즈·dispose 시험 없음 · 배선 시험은 문자열 대조뿐.
NIT-1 배경색만 있는 빈 줄을 빈 줄로 본다(trim) — 배너가 그 위에 앉아 배경색이 남을 수 있음.
NIT-2 판독 시점과 배너 해석 사이 리사이즈(12ms 쓰기 예산이 reset 청크에서 끊길 때만) — 확률 매우 낮음 · 소스 추론(미시험).
NIT-3 콜백 안 예외는 xterm 쓰기 대기열을 멈출 수 있음(50MB 폐기선 너머 또는 done 이 던질 때) — snapToBottom 콜백은 종전에도 같은 노출.
NIT-4 dispose 뒤 콜백: 실행되거나(판독은 try) 안 됨 — 배너 2회·우리 코드 예외 불가. rows=1 은 setScrollRegion 가드.
Windows/ConPTY(추론): ConPTY 는 대체 화면·스크롤 영역을 자기 주 화면 프레임으로 그려 MINOR-1·ESC[r 경로는 대부분 무관 · 커서 중간 잔류는 이 수리가 덮음 · 지운 줄은 기본 속성 공백이라 trim 이 처리.
