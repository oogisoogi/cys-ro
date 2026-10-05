//! 1.1.8 데몬 자동 갱신 — 공용 모듈(U1 · 피드·검증·판정). 설계 정본 = AUTO-UPDATE-118 4판
//! (`~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md`).
//!
//! U1 범위 = 판정까지(교체·rotate·롤백·앱 UI 0 — U2·U4). 이 모듈의 함수는 대부분 순수 함수이고, 파일을 쓰는 것
//! (수용 기록·잠금·저널·보류 로그·install_id)은 상태 폴더([`state_dir`]) 아래에만 쓴다. 시험은 `CYS_UPDATE_STATE_DIR`
//! 로 격리한다(실 `~/.cys` 쓰기 0).

pub mod buildinfo;
pub mod clock;
pub mod errors;
pub mod feed;
pub mod gates;
pub mod hold;
pub mod journal;
pub mod keys;
pub mod lock;
pub mod packgate;
pub mod sched;
pub mod url;
pub mod win;

/// 원작자 윈 설치기 실행 판정(📌15 편입 · 파일 통째 · `src/update_launch.rs` 그 자리 그대로 — 아래 근거).
///
/// 설계 §5-1 은 `src/update/launch_win.rs` 로 옮긴다고 적었으나, 파일 위치를 옮기면 ① 윈 실기 레인
/// (`windows-health.yml`)의 시험 필터 `update_launch::` 와 ② 앱 핀 시험의 `include_str!("../../src/update_launch.rs")` 가
/// 깨진다(CI 워크플로 변경 = master 게이트). 그래서 파일은 그대로 두고 여기서 같은 모듈을 `launch_win` 이름으로 노출한다
/// — 바이트 동일성(`git hash-object`)은 그대로 유지된다.
pub use crate::update_launch as launch_win;

pub use errors::{ErrCode, UpdateErr};
