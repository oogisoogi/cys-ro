// TICKET=cysr-cli-stack-probe — 스택 칠하기(painting) 탐침. 전부 `#[ignore]` · 동작 코드 무변.
// 실행: `RUST_MIN_STACK=16777216 cargo test --bin cys stack_probe -- --ignored --nocapture --test-threads=1`
// 원리: 지금 틀 아래 PAINT 바이트를 표식(0xA5)으로 칠하고 → 일감을 돌리고 → 아래에서 위로 훑어 처음 지워진 바이트 =
// 일감의 최저 수위. 스레드 꼭대기(pthread_get_stackaddr_np)에서 그 수위까지 = 이 스레드가 쓴 스택 전체.
// 큰 틀은 머리말 탐침(`str xzr, [sp]`, 쪽마다)이 0 을 쓰므로 칠이 지워진다 = 탐침이 닿은 곳까지 잡힌다.
use super::*;
use std::hint::black_box;

const PAINT: usize = 6 << 20;
const MARK: u8 = 0xA5;

fn top() -> usize {
    unsafe { libc::pthread_get_stackaddr_np(libc::pthread_self()) as usize }
}
fn size() -> usize {
    unsafe { libc::pthread_get_stacksize_np(libc::pthread_self()) }
}
#[inline(never)]
fn here() -> usize {
    let x = 0u8;
    black_box(&x) as *const u8 as usize
}
#[inline(never)]
fn paint() -> usize {
    let mut buf = [0u8; PAINT];
    for b in buf.iter_mut() {
        unsafe { std::ptr::write_volatile(b, MARK) }
    }
    black_box(&mut buf).as_ptr() as usize
}
#[inline(never)]
fn low_water(lo: usize) -> usize {
    let p = lo as *const u8;
    let mut i = 0;
    while i < PAINT && unsafe { std::ptr::read_volatile(p.add(i)) } == MARK {
        i += 1;
    }
    lo + i
}
/// (꼭대기에서 일감 최저 수위까지 쓴 바이트, 일감 진입 직전 꼭대기에서의 깊이)
#[inline(never)]
fn measure(f: &dyn Fn()) -> (usize, usize) {
    let t = top();
    let entry = t - here();
    let lo = paint();
    f();
    (t - low_water(lo), entry)
}
fn report(name: &str, f: &dyn Fn()) {
    let (used, entry) = measure(f);
    println!("PROBE {name}: used_from_top={used} entry_depth={entry} body={} thread_size={}", used - entry, size());
}

#[test]
#[ignore]
fn stack_probe_thread_facts() {
    // 기본 스레드 크기·꼭대기에서 시험 함수까지 깊이(libtest·스레드 시작 틀)
    println!("PROBE facts: thread_size={} test_fn_depth={}", size(), top() - here());
}

#[test]
#[ignore]
fn stack_probe_cli_parse() {
    use clap::Parser;
    report("noop", &|| {});
    report("Cli::command", &|| {
        black_box(<Cli as clap::CommandFactory>::command());
    });
    for c in [
        "cys kill 123",
        "cys pause",
        "cys channel --help",
        "cys launch-agent --role worker --agent claude --cwd /a/hq",
        "cys kill 123 2",
    ] {
        let toks: Vec<String> = c.split_whitespace().map(String::from).collect();
        report(&format!("try_parse_from[{c}]"), &|| {
            black_box(Cli::try_parse_from(toks.iter()).is_ok());
        });
    }
    report("a3_test_body", &|| a3_strip_hook_digits_only_for_the_seven_target_verbs_when_the_rest_is_leftover_args());
}

/// 같은 일감(a3 본문)의 최저 수위가 **조용할 때**와 **다른 스레드가 할당기를 두드릴 때** 달라지는가 — N회 분포.
fn a3_spread(label: &str, n: usize) {
    let mut v: Vec<usize> = (0..n)
        .map(|_| measure(&|| a3_strip_hook_digits_only_for_the_seven_target_verbs_when_the_rest_is_leftover_args()).0)
        .collect();
    v.sort();
    let mut hist: std::collections::BTreeMap<usize, usize> = std::collections::BTreeMap::new();
    for x in &v {
        *hist.entry(*x).or_default() += 1;
    }
    println!("PROBE spread[{label}] n={n} min={} max={} hist={:?}", v[0], v[n - 1], hist);
}

#[test]
#[ignore]
fn stack_probe_a3_quiet() {
    a3_spread("quiet", 200);
}

#[test]
#[ignore]
fn stack_probe_a3_alloc_storm() {
    let stop = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));
    let hs: Vec<_> = (0..12usize)
        .map(|k| {
            let stop = stop.clone();
            std::thread::spawn(move || {
                let mut keep: Vec<Vec<u8>> = Vec::new();
                let mut i = k;
                while !stop.load(std::sync::atomic::Ordering::Relaxed) {
                    i = i.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
                    let sz = [16usize, 48, 200, 1024, 4000, 40_000, 300_000][i % 7];
                    keep.push(vec![1u8; sz]);
                    if keep.len() > 64 {
                        keep.swap_remove(i % 64);
                    }
                }
            })
        })
        .collect();
    a3_spread("alloc_storm", 200);
    stop.store(true, std::sync::atomic::Ordering::Relaxed);
    for h in hs {
        let _ = h.join();
    }
}

/// 여유(바이트) 재기: 기본 시험 스레드(RUST_MIN_STACK 없이)에서 고정 크기 틀을 STACK_PROBE_PAD 단 쌓은 뒤 a3 본문을 부른다.
/// 프로세스마다 하나의 값 — 넘치면 프로세스가 죽는다(바깥 스크립트가 이분법). 한 단 크기는 `frame_size.py ... stack_probe3pad`.
#[inline(never)]
fn pad(n: usize, f: &dyn Fn()) {
    let b = [0u8; 16];
    black_box(&b);
    if n == 0 {
        f()
    } else {
        pad(n - 1, f)
    }
}

fn storm(on: bool) -> (std::sync::Arc<std::sync::atomic::AtomicBool>, Vec<std::thread::JoinHandle<()>>) {
    let stop = std::sync::Arc::new(std::sync::atomic::AtomicBool::new(false));
    let hs = if !on {
        Vec::new()
    } else {
        (0..12usize)
            .map(|k| {
                let stop = stop.clone();
                std::thread::spawn(move || {
                    let mut keep: Vec<Vec<u8>> = Vec::new();
                    let mut i = k;
                    while !stop.load(std::sync::atomic::Ordering::Relaxed) {
                        i = i.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
                        let sz = [16usize, 48, 200, 1024, 4000, 40_000, 300_000][i % 7];
                        keep.push(vec![1u8; sz]);
                        if keep.len() > 64 {
                            keep.swap_remove(i % 64);
                        }
                    }
                })
            })
            .collect()
    };
    (stop, hs)
}

#[test]
#[ignore]
fn stack_probe_a3_margin() {
    let n: usize = std::env::var("STACK_PROBE_PAD").ok().and_then(|s| s.parse().ok()).unwrap_or(0);
    let reps: usize = std::env::var("STACK_PROBE_REPS").ok().and_then(|s| s.parse().ok()).unwrap_or(1);
    let (stop, hs) = storm(std::env::var("STACK_PROBE_STORM").is_ok());
    println!("PROBE margin: thread_size={} test_fn_depth={} pad={n}", size(), top() - here());
    for _ in 0..reps {
        pad(n, &|| a3_strip_hook_digits_only_for_the_seven_target_verbs_when_the_rest_is_leftover_args());
    }
    stop.store(true, std::sync::atomic::Ordering::Relaxed);
    for h in hs {
        let _ = h.join();
    }
}

/// 부하만 낸다(STACK_PROBE_STORM_SECS 초) — 진짜 a3 시험과 같은 프로세스에서 나란히 돌리는 짝.
#[test]
#[ignore]
fn stack_probe_storm_only() {
    let secs: u64 = std::env::var("STACK_PROBE_STORM_SECS").ok().and_then(|s| s.parse().ok()).unwrap_or(3);
    let (stop, hs) = storm(true);
    std::thread::sleep(std::time::Duration::from_secs(secs));
    stop.store(true, std::sync::atomic::Ordering::Relaxed);
    for h in hs {
        let _ = h.join();
    }
}
