// selfdiag.ts — 자가진단·CEO 승격 팔레트 노출 결정(D4 · 결정 D4)의 순수 로직.
//
// 팔레트에는 CEO 관련 항목이 둘 있다: 'CEO 승격 진행'(PENDING 티켓 해소=promote_pending_ceo)과
// 'CEO 승격 재실행(템플릿 전진 적용)'(드리프트 해소=approve_ceo_promotion). 두 신호가 동시에 참인
// 비정형 창(승격 뒤 새 PENDING 생성 등)에서 둘을 같이 띄우면 오너가 순서를 고를 수 없고, '재실행'이
// 먼저 눌리면 최초 승격 절차(부트 게이트 경유)가 역전된다 — 그래서 **상호 배타·pending 우선**을
// 여기 순수 함수 하나로 고정한다(main.ts 는 이 결과를 그대로 배선만 한다).

/// 데몬/파일 실측 신호(각 invoke 는 실패 시 false 로 접힌다 — 노출 억제가 안전 기본값).
export interface CeoGateSignals {
  /// ~/.cys/state/ceo-pending 존재 — 최초 승격이 부트 게이트로 보류된 상태(ceo_pending).
  pending: boolean;
  /// .pre-ceo 존재 ∧ md≠라이브 CEO_TEMPLATE — 승격본이 릴리스 전진으로 구본화(ceo_promotion_drift).
  drift: boolean;
}

export type CeoPaletteEntry = "pending" | "repromote";

/// 노출할 CEO 팔레트 항목(0~1개). pending 이 항상 우선한다(최초 승격 미완에 '재실행' 권유 금지).
export function ceoPaletteEntries(g: CeoGateSignals): CeoPaletteEntry[] {
  if (g.pending) return ["pending"];
  if (g.drift) return ["repromote"];
  return [];
}

// ★A-Z14(v116-ceo-hold-az14): 승격 명령(approve_ceo_promotion = cys-dept promote-ceo)의 실패·보류 알림.
// cys-dept 는 지침이 CEO 로 바뀌지 않았으면 exit 5(보류)를 내고, 백엔드는 그 Err 앞에 `이 태그 + 사유:` 를 단다
// (src-tauri ceo_promote_result — 사유 boot = 본부 master 미부트 · other = 그 밖 · 같은 문자열을 Rust 시험이 대조한다).
// 보류는 「실패」가 아니라 「아직 안 바꿈」이라 문구·등급을 가른다 — 종전에는 보류가 exit 0 으로 새어
// 「✅ 승격 완료」로 오보됐다(1098 형상 · 낡은 백업 + 미부트).
export const CEO_PROMOTE_HELD_TAG = "ceo_promote_held:";

export interface CeoPromoteFailToast {
  held: boolean;
  /// 보류 사유가 「본부 마스터 미부트」인가(백엔드 사유 태그 boot).
  boot: boolean;
  /// 알림 등급 — 보류 = feed(안내) · 실패 = health(경보).
  category: "feed" | "health";
  title: string;
  body: string;
  /// 「자세히」에 넣을 원문 — 기계 태그·사유는 떼어 낸다.
  raw: string;
}

const HELD_BOOT_BODY =
  "아직 CEO로 바꾸지 않았어요. 지금 설정은 그대로예요. 본부 마스터를 먼저 한 번 시작한 뒤 다시 눌러 주세요.";
// 재실행 경로의 부트 보류: 보류가 대기 표시(ceo-pending)를 남기면 팔레트 항목이 「CEO 승격 진행」으로 바뀐다
//   (ceoPaletteEntries 의 pending 우선) — 「다시 눌러」 대상이 사라지므로 바뀐 항목 이름을 안내한다(Opus R2 NOTE).
const HELD_BOOT_BODY_REPROMOTE =
  "아직 CEO로 바꾸지 않았어요. 지금 설정은 그대로예요. 본부 마스터를 먼저 한 번 시작한 뒤, 명령 팔레트의 「CEO 승격 진행」을 눌러 주세요.";

/// 승격 실패/보류 알림. repromote = 팔레트 '재실행'(새 템플릿을 다시 적용) 경로.
export function ceoPromoteFailToast(err: unknown, repromote: boolean): CeoPromoteFailToast {
  const s = String(err);
  const at = s.indexOf(CEO_PROMOTE_HELD_TAG);
  if (at < 0) {
    return repromote
      ? { held: false, boot: false, category: "health", title: "CEO 승격 재실행 실패", raw: s,
          body: "새 설정으로 CEO 자리를 다시 세우지 못했습니다. 잠시 뒤 다시 시도해 주세요." }
      : { held: false, boot: false, category: "health", title: "CEO 승격 실패", raw: s,
          body: "CEO 자리를 세우지 못했습니다. 요청은 그대로 남아 있으니 잠시 뒤 다시 시도해 주세요." };
  }
  const rest = s.slice(at + CEO_PROMOTE_HELD_TAG.length);
  const boot = rest.startsWith("boot:");
  const raw = rest.replace(/^(boot|other):/, "");
  const title = repromote ? "CEO 승격 재실행 보류" : "CEO 승격 보류";
  if (boot) return { held: true, boot, category: "feed", title, raw, body: repromote ? HELD_BOOT_BODY_REPROMOTE : HELD_BOOT_BODY };
  return {
    held: true, boot, category: "feed", title, raw,
    body: repromote
      ? "새 설정을 아직 적용하지 않았어요. 지금 쓰던 설정은 그대로예요. 이유는 알림의 「자세히」를 눌러 확인해 주세요."
      : "아직 CEO로 바꾸지 않았어요. 지금 설정은 그대로예요. 이유는 알림의 「자세히」를 눌러 확인해 주세요.",
  };
}
