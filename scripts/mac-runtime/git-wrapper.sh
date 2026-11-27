#!/bin/sh
# cys(1.1.21 A): 동봉 dugite git 자립 감싸개 — 정본 = 이 파일(저장소 scripts/mac-runtime/git-wrapper.sh) · 번들 자리 = Contents/Resources/runtime/git/cysbin/git
# dugite git 은 --exec-path 가 빌드 접두(//libexec/git-core)로 박혀 있어, 부르는 쪽이 GIT_EXEC_PATH 를
# 넣어 주지 않으면 https(remote-https 헬퍼)를 못 찾고 init 템플릿도 못 찾는다. 이 감싸개가 자기 자리
# (runtime/git/cysbin) 기준으로 GIT_EXEC_PATH(항상)·GIT_TEMPLATE_DIR(비었을 때만)를 세우고 진짜
# 바이너리(libexec/git-core/git)를 부른다. 템플릿은 아래 규칙(init·clone · 사용자 무선택일 때만).
# ★GIT_CONFIG_SYSTEM 은 세우지 않는다: ① `git config --system …` 이 번들 안 etc/gitconfig 에 써서 앱
#   봉인을 깬다 ② git 이 띄우는 자식(훅 등)이 절대 경로로 다른 git(Homebrew)을 부르면 그 git 의 system
#   설정(credential helper 등)을 가린다. 세우지 않으면 system 설정 = /etc/gitconfig(dugite 접두 "/" 기준 ·
#   dugite gitconfig 도 이것을 include 할 뿐이다).
_cys_self=$0
_cys_n=0
# 심링크로 불렸으면 실체까지 따라간다(상대 링크는 링크가 있는 dir 기준 · 순환 링크 대비 상한 40).
while [ -h "$_cys_self" ] && [ "$_cys_n" -lt 40 ]; do
  _cys_n=$((_cys_n + 1))
  _cys_link=$(/usr/bin/readlink "$_cys_self") || break
  case $_cys_link in
    /*) _cys_self=$_cys_link ;;
    *) _cys_self=${_cys_self%/*}/$_cys_link ;;
  esac
done
case $_cys_self in
  */*) _cys_dir=${_cys_self%/*} ;;
  *) _cys_dir=. ;;
esac
case $_cys_dir in
  /*) ;;
  *) _cys_dir=$(pwd)/$_cys_dir ;;
esac
_cys_root=$(cd "$_cys_dir/.." 2>/dev/null && pwd -P) || _cys_root=$_cys_dir/..
GIT_EXEC_PATH=$_cys_root/libexec/git-core
export GIT_EXEC_PATH
# 템플릿 기본값은 init·clone 에만, 사용자가 고르지 않았을 때만 준다(git 우선순위 --template > env >
# init.templateDir 설정 > 컴파일 기본 — env 를 무조건 세우면 사용자 init.templateDir 을 가린다).
# 하위 명령 찾기: 앞쪽 전역 옵션을 건너뛴다(값을 다음 인자로 받는 것은 그 값까지).
# 설정 조회는 init·clone 이 실제로 읽는 설정만 본다 = system · global · 명령줄(-c · --config-env) · env
# (GIT_CONFIG_COUNT 등). 저장소 로컬 설정은 init·clone 이 쓰지 않으므로(실측: -C <repo> 의 로컬 init.templateDir
# 은 무시됨) 조회는 저장소 밖(/)에서 GIT_DIR·GIT_WORK_TREE 없이 돌린다. GIT_CONFIG(옛 env · `git config` 명령에만
# 먹고 init·clone 의 설정 읽기에는 안 먹음)도 조회에서만 지운다(codex r5).
# GIT_CONFIG_GLOBAL·GIT_CONFIG_SYSTEM·XDG_CONFIG_HOME 가운데 하나라도 상대 경로면 조회하지 않고 보류한다
# (그 뜻은 git 이 -C·init 대상 폴더로 옮긴 뒤 정해져 조회가 같은 자리를 재현할 수 없다 · Fable r5 권고).
# 조회 결과: 0 = 설정 있음(사용자 선택) · 1 = 없음(기본값 줌) · 그 밖 = 판단 보류(주지 않음).
# 값을 다음 인자로 받는 git 전역 옵션(하위 명령 찾기·조회 인자 수집이 함께 쓰는 단일 목록).
_cys_valopt() {
  case $1 in
    -C|-c|--git-dir|--work-tree|--namespace|--super-prefix|--config-env|--exec-path|--attr-source) return 0 ;;
  esac
  return 1
}
_cys_probe_tpl() {
  for _cys_v in "${GIT_CONFIG_GLOBAL-}" "${GIT_CONFIG_SYSTEM-}" "${XDG_CONFIG_HOME-}"; do
    case $_cys_v in
      ''|/*) ;;
      *) return 2 ;;
    esac
  done
  _cys_k=$1
  shift
  _cys_n=$#
  _cys_i=0
  _cys_take=
  for _cys_a do
    _cys_i=$((_cys_i + 1))
    [ "$_cys_i" -le "$_cys_k" ] || continue
    if [ -n "$_cys_take" ]; then
      # 값 받는 전역 옵션의 값: -c·--config-env 는 조회에 싣고, 그 밖(-C·--git-dir 등)은 버린다.
      case $_cys_take in -c|--config-env) set -- "$@" "$_cys_take" "$_cys_a" ;; esac
      _cys_take=
      continue
    fi
    case $_cys_a in
      --config-env=*) set -- "$@" "$_cys_a" ;;
      -*) if _cys_valopt "$_cys_a"; then _cys_take=$_cys_a; fi ;;
    esac
  done
  shift "$_cys_n"
  (unset GIT_DIR GIT_WORK_TREE GIT_CONFIG; cd / && "$GIT_EXEC_PATH/git" "$@" config --get init.templateDir >/dev/null 2>&1)
}
if [ -z "${GIT_TEMPLATE_DIR+x}" ]; then
  _cys_sub=
  _cys_skip=
  _cys_pos=0
  for _cys_a in "$@"; do
    if [ -n "$_cys_skip" ]; then _cys_skip=; _cys_pos=$((_cys_pos + 1)); continue; fi
    case $_cys_a in
      -*) if _cys_valopt "$_cys_a"; then _cys_skip=1; fi ;;
      *) _cys_sub=$_cys_a; break ;;
    esac
    _cys_pos=$((_cys_pos + 1))
  done
  case $_cys_sub in
    init|clone)
      _cys_tpl=1
      for _cys_a in "$@"; do
        case $_cys_a in --template|--template=*) _cys_tpl= ;; esac
      done
      if [ -n "$_cys_tpl" ]; then
        _cys_probe_tpl "$_cys_pos" "$@"
        case $? in 1) ;; *) _cys_tpl= ;; esac
      fi
      if [ -n "$_cys_tpl" ]; then
        GIT_TEMPLATE_DIR=$_cys_root/share/git-core/templates
        export GIT_TEMPLATE_DIR
      fi
      ;;
  esac
  unset _cys_sub _cys_skip _cys_pos _cys_a _cys_tpl _cys_k _cys_n _cys_i _cys_take _cys_v
fi
unset _cys_self _cys_link _cys_dir _cys_root _cys_n
exec "$GIT_EXEC_PATH/git" "$@"
