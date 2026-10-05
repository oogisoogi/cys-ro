//! 1.1.8 데몬 자동 갱신 — 공용 모듈(U1 · 피드·검증·판정). 설계 정본 = AUTO-UPDATE-118 4판
//! (`~/axdev/master/reports/cysr-118-plan/DESIGN-AUTOUPDATE-118.md`).
//!
//! U1 범위 = 판정까지(교체·rotate·롤백·앱 UI 0 — U2·U4). 이 모듈의 함수는 대부분 순수 함수이고, 파일을 쓰는 것
//! (수용 기록·잠금·저널·보류 로그·install_id)은 상태 폴더([`state_dir`]) 아래에만 쓴다. 시험은 `CYS_UPDATE_STATE_DIR`
//! 로 격리한다(실 `~/.cys` 쓰기 0).

pub mod clock;
pub mod errors;
pub mod feed;
pub mod keys;
pub mod url;

pub use errors::{ErrCode, UpdateErr};
