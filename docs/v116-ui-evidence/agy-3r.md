BLOCK

MAJOR: `masterIdleCopy` 함수에서 기존 원문에 포함되어 있던 임계 시간(`payload.threshold_secs`) 정보가 누락되어, 발주 조건의 "③사실(번호·%·시간·사유) 유지" 규율을 위반했습니다.
- `body: \`${seatName(no, role)}에서 \${durText(p.idle_secs)} 동안 새 출력이 없습니다. 기다리는 중일 수 있으니 오래 이어지면 \${CHECK}\`,`
