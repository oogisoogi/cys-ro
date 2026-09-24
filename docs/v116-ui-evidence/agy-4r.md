**BLOCK**

**MINOR**
Fable의 5번 지적(부서 이벤트 시 창 번호가 본부와 겹치므로 부서 이름 접두)을 반영하기 위해 `seatName` 함수가 개편되고 대부분의 알림에 적용되었으나, `roleTakeoverCopy`에서는 이를 사용하지 않고 여전히 창 번호를 하드코딩하고 있습니다. 이로 인해 부서 데몬에서 발생한 좌석 승계 이벤트의 경우 부서 접두사가 누락되어 어떤 창인지 모호해집니다.

```typescript
 export function roleTakeoverCopy(prevNo: number | null, p: Record<string, unknown>): AlertCopy {
   const name = friendlyRole(typeof p.role === "string" ? p.role : "master");
-  const prev = prevNo != null ? `${prevNo}번 창` : "옛 창";
+  // 수정 필요: prevNo != null ? seatName(prevNo, null, p.dept) : "옛 창";
   return {
     title: `ℹ ${name} 자리가 다른 창으로 옮겨졌습니다`,
     body: `${prev}이 비어 있어 이 역할을 새 창으로 옮겨 붙였습니다. 옛 창에 전할 말이 남아 있으면 그대로 둡니다.`,
   };
 }
```
