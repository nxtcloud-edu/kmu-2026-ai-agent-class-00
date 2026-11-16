"""내 에이전트 플랫폼 템플릿(my-agent-platform)의 Windows 확인 스크립트. 표준 라이브러리만 쓴다.

레포를 받은 폴더의 PowerShell에서 실행한다. 결과 파일은 이 스크립트가 있는 windows_test 폴더에 생긴다.

  python windows_test\\windows_check.py           기본 확인: 환경, 단위 테스트, 엔진의 설치와 로그인 상태.
                                                  엔진을 부르지 않아 사용량이 없다. 1~3분 걸린다.
                                                  결과: windows_check_기본.txt

  python windows_test\\windows_check.py --real    실제 엔진 확인: 로그인된 엔진마다 짧은 질문 4개를 보낸다.
                                                  사용량이 조금 든다. 엔진마다 1~3분 걸린다.
                                                  결과: windows_check_실제엔진.txt

--real에서는 개인 스킬 격리 확인을 할지 묻는다. 하면 사용자 폴더의 스킬 폴더
(.kiro\\skills, .claude\\skills, .agents\\skills)에 acp-starter-marker 폴더를 잠깐 만들었다가 지운다.
"""

import argparse
import datetime
import locale
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback

IS_WINDOWS = os.name == "nt"
MARKER = "acp-starter-marker"
MARKER_DIRS = {"kiro": (".kiro", "skills"), "claude": (".claude", "skills"), "codex": (".agents", "skills")}
STEP_SECONDS = 300                                # 질문 하나를 기다리는 최대 시간
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")         # 색 코드. 결과 파일에서 지운다
NOTE = "windows_check_메모.md"                    # 실제 엔진 확인에서 엔진이 작업 폴더에 쓰는 파일

try:
    sys.stdout.reconfigure(errors="replace")      # 화면이 cp949여도 출력이 멈추지 않게 한다
except (AttributeError, ValueError):
    pass


class Report:
    """화면에 보이면서 같은 내용을 결과 파일에 모은다."""

    def __init__(self, path):
        self.path = path
        self.lines = []

    def say(self, text=""):
        print(text, flush=True)
        self.lines.append(str(text))

    def save(self):
        # 메모장에서도 한글이 깨지지 않게 BOM이 있는 UTF-8로 쓴다.
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8-sig")


def run(args, timeout=60, cwd=None):
    """명령을 실행하고 (종료 코드, 출력)을 돌려준다. 실행하지 못하면 (None, 까닭)."""
    env = dict(os.environ, NO_COLOR="1", PYTHON_COLORS="0", PYTHONIOENCODING="utf-8")
    try:
        done = subprocess.run(args, capture_output=True, encoding="utf-8", errors="replace",
                              timeout=timeout, cwd=cwd, env=env)
    except FileNotFoundError:
        return None, "찾지 못함"
    except subprocess.TimeoutExpired:
        return None, f"{timeout}초 안에 끝나지 않음"
    except OSError as error:
        return None, f"실행 오류: {error}"
    return done.returncode, ANSI.sub("", (done.stdout or "") + (done.stderr or "")).strip()


def yesno(value):
    return {True: "예", False: "아니오", None: "알 수 없음"}.get(value, str(value))


def one_line(text, limit=1200):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit] + " …"


# ---- 1. 환경 ----

def check_environment(report, repo):
    report.say("## 1. 환경")
    report.say(f"- 시각: {datetime.datetime.now():%Y-%m-%d %H:%M}")
    report.say(f"- 운영체제: {platform.platform()}")
    if IS_WINDOWS:
        version = sys.getwindowsversion()
        edition = "Windows 11" if version.build >= 22000 else "Windows 10 이하"
        report.say(f"- Windows 빌드: {version.major}.{version.minor}.{version.build} ({edition})")
    report.say(f"- Python: {sys.version.split()[0]} ({sys.executable})")
    report.say(f"- 인코딩: 파일 이름 {sys.getfilesystemencoding()}, 기본 {locale.getpreferredencoding(False)}, "
               f"화면 {sys.stdout.encoding}, PYTHONUTF8={os.environ.get('PYTHONUTF8', '(없음)')}")
    home = pathlib.Path.home()
    report.say(f"- 사용자 폴더 이름에 영문 밖 글자(한글 등): {'있음' if not str(home).isascii() else '없음'}")
    report.say(f"- 레포 위치: {repo}")
    report.say(f"  OneDrive 아래: {'예' if 'onedrive' in str(repo).lower() else '아니오'}, "
               f"영문 밖 글자: {'있음' if not str(repo).isascii() else '없음'}")
    sample = repo / "custom" / "brand.json"
    if sample.is_file():
        crlf = b"\r\n" in sample.read_bytes()
        report.say(f"- 레포 파일의 줄 끝: {'CRLF(Windows 꼴)' if crlf else 'LF'}")

    report.say("")
    report.say("도구:")
    for name, args in [("git", ["--version"]), ("node", ["-v"]), ("npm", ["-v"]), ("npx", ["-v"]),
                       ("kiro-cli", ["--version"]), ("claude", ["--version"]), ("codex", ["--version"]),
                       ("python", ["--version"]), ("python3", ["--version"]), ("py", ["--version"])]:
        path = shutil.which(name)
        if not path:
            report.say(f"- {name}: 없음")
            continue
        code, out = run([path, *args], timeout=60)
        first = out.splitlines()[0] if out else "(출력 없음)"
        note = ""
        if "WindowsApps" in path and name.startswith("python"):
            note = "  ← Microsoft Store 별칭이다. 이 이름으로는 실행하지 않는다"
        report.say(f"- {name}: {first}  [{path}]{note}")
    code, out = run(["git", "config", "--get", "core.autocrlf"], timeout=30)
    report.say(f"- git core.autocrlf: {out or '(설정 없음)'}")
    if IS_WINDOWS:
        code, out = run(["powershell", "-NoProfile", "-Command", "Get-ExecutionPolicy"], timeout=60)
        report.say(f"- PowerShell 실행 정책: {out or code}")
    report.say("")


# ---- 2. 단위 테스트 ----

def check_unit_tests(report, repo):
    report.say("## 2. 단위 테스트 (가짜 엔진, 사용량 없음)")
    report.say("  (몇 분 걸린다. 끝날 때까지 창을 닫지 않는다)")
    started = time.time()
    code, out = run([sys.executable, "-m", "unittest", "discover", "tests"], timeout=1800, cwd=repo)
    summary = [line for line in out.splitlines() if line.startswith(("Ran ", "OK", "FAILED"))]
    report.say(f"- 결과: {' / '.join(summary) or out[-300:]} ({time.time() - started:.0f}초)")
    if code != 0:
        report.say("- 실패한 테스트의 내용(뒤에서 250줄):")
        for line in out.splitlines()[-250:]:
            report.say("    " + line)
    report.say("")


# ---- 3. 엔진 상태 ----

def check_engines(report, engines):
    report.say("## 3. 엔진의 설치와 샌드박스 로그인 상태")
    states = {}
    for name in engines.names():
        cls = engines.get(name)
        try:
            installed = cls.installed()
            logged = cls.check_login() if installed else None
        except Exception as error:  # 어떤 오류든 기록하고 다음 엔진으로 간다
            installed, logged = f"오류 {type(error).__name__}: {error}", None
        states[name] = (installed, logged)
        report.say(f"- {name}: 설치 {yesno(installed)}, 로그인 {yesno(logged)}")
    report.say("  (Claude와 Codex는 레포 안 .homes의 샌드박스에 따로 로그인한다. 앱의 엔진 카드에서 한다)")
    report.say("")
    return states


# ---- 4. 실제 엔진 ----

def process_table():
    """지금 도는 프로세스: 번호 → (부모 번호, 이름)."""
    if IS_WINDOWS:
        script = 'Get-CimInstance Win32_Process | ForEach-Object { "$($_.ProcessId),$($_.ParentProcessId),$($_.Name)" }'
        code, out = run(["powershell", "-NoProfile", "-Command", script], timeout=120)
        rows = [line.split(",", 2) for line in out.splitlines()]
    else:
        code, out = run(["ps", "-axo", "pid=,ppid=,comm="], timeout=60)
        rows = [line.split(None, 2) for line in out.splitlines()]
    table = {}
    for row in rows:
        if len(row) == 3 and row[0].strip().isdigit() and row[1].strip().isdigit():
            table[int(row[0])] = (int(row[1]), pathlib.Path(row[2].strip()).name)
    return table


def family(root):
    """root 프로세스와 그 아래로 이어진 모든 프로세스: 번호 → 이름. 엔진은 npx, node, 엔진 프로그램으로 이어진다."""
    table, found, queue = process_table(), {}, [root]
    while queue:
        pid = queue.pop()
        if pid in table and pid not in found:
            found[pid] = table[pid][1]
            queue += [child for child, (parent, _) in table.items() if parent == pid]
    return found


def leftover(tree, seconds=15):
    """엔진을 닫은 뒤 그 프로세스들이 끝나는지 기다려 본다."""
    started = time.time()
    while True:
        table = process_table()
        alive = sorted(name for pid, name in tree.items() if pid in table and table[pid][1] == name)
        if not alive:
            return f"엔진 프로세스 {len(tree)}개가 {time.time() - started:.0f}초 안에 모두 끝남"
        if time.time() - started >= seconds:
            return f"엔진 프로세스 {len(tree)}개 중 {seconds}초 뒤에도 남은 것 {alive}"
        time.sleep(1)


def ask(client, text, files=(), seconds=STEP_SECONDS):
    """질문 하나를 보내고 TurnResult를 돌려준다. 너무 오래 걸리면 엔진을 닫아 멈춘다."""
    timer = threading.Timer(seconds, client.close)
    timer.start()
    try:
        return client.send(text, list(files))
    finally:
        timer.cancel()


def check_real(report, engines, custom_loader, repo, states, only, marker_home):
    report.say("## 4. 실제 엔진 (로그인된 엔진마다 짧은 질문 4개)")
    workspace = repo / "workspace"
    note = workspace / NOTE
    preamble = custom_loader.preamble(repo / "custom")
    for name in engines.names():
        installed, logged = states[name]
        if only and name not in only:
            continue
        if installed is not True or logged is not True:
            report.say(f"### {name}: 건너뜀 (설치 {yesno(installed)}, 로그인 {yesno(logged)})")
            continue
        report.say(f"### {name}")
        asked, rule, tree = [], [lambda request: False], {}
        note.unlink(missing_ok=True)

        def on_permission(request):
            allow = bool(rule[0](request))
            detail = request.detail.splitlines()[0][:200] if request.detail else ""
            asked.append(f"{'허락' if allow else '거절'} {request.label}: {detail}  (kind={request.kind}, path={request.path!r})")
            return allow

        def runs(*words):
            return lambda request: request.kind == "execute" and all(w in (request.command or request.detail) for w in words)

        def writes(request):
            return request.kind == "edit" and NOTE in (request.path or request.detail)

        steps = [
            ("인사", "한 단어로만 답한다: 안녕", lambda request: False),
            ("명령 실행", "셸 명령으로 파이썬의 버전을 확인한다. 실행한 명령과 그 출력만 그대로 적는다. "
                         "파이썬을 찾지 못하면 그 오류를 그대로 적는다.", runs("version")),
            ("파일 쓰기(허락)", f"작업 폴더에 {NOTE} 파일을 만들고 그 안에 '확인'이라고만 적는다. 한 문장으로 결과를 답한다.", writes),
            ("파일 쓰기(거절)", f"작업 폴더의 {NOTE} 파일에 '둘째 줄'이라는 줄을 더한다. 허락되지 않으면 다른 방법을 쓰지 말고 "
                              "하지 못했다고 한 문장으로 답한다.", lambda request: False),
        ]
        client = engines.make(name, workspace, on_permission=on_permission, preamble=preamble)
        try:
            started = time.time()
            client.start()
            report.say(f"- 연결: {time.time() - started:.1f}초, 엔진이 받는 질문 형식 {client.prompt_capabilities}")
            for label, text, step_rule in steps:
                rule[0] = step_rule
                asked.clear()
                started = time.time()
                result = ask(client, text)
                report.say(f"- {label}: {result.stop_label}, {time.time() - started:.0f}초")
                report.say(f"    답: {one_line(result.text)}")
                for line in asked:
                    report.say(f"    허락 요청 · {line}")
                for notice in result.notices:
                    report.say(f"    플랫폼 알림 · {notice}")
                if label.startswith("파일 쓰기"):
                    body = note.read_text(encoding="utf-8", errors="replace") if note.is_file() else None
                    report.say(f"    {NOTE}: {'없음' if body is None else repr(body[:80])}")
        except Exception as error:  # 엔진 오류를 기록하고 다음 엔진으로 간다
            report.say(f"- 오류: {type(error).__name__}: {error}")
            for line in traceback.format_exc().splitlines()[-12:]:
                report.say("    " + line)
        finally:
            if client.process is not None:
                tree = family(client.process.pid)
            client.close()
        report.say(f"- 엔진 프로세스: {sorted(tree.values())}")
        report.say(f"- 엔진을 닫은 뒤: {leftover(tree) if tree else '엔진 프로세스를 찾지 못함'}")
        note.unlink(missing_ok=True)
        if marker_home:
            check_marker(report, engines, name, workspace, preamble, marker_home)
    report.say("")


def check_marker(report, engines, name, workspace, preamble, marker_home):
    """사용자 폴더의 개인 스킬이 플랫폼 안의 엔진에 새어 드는지 본다. 표시용 스킬을 잠깐 만들었다가 지운다."""
    base = marker_home.joinpath(*MARKER_DIRS[name])
    folder = base / MARKER
    if folder.exists():
        report.say(f"- 개인 스킬 격리: 건너뜀 ({folder}가 이미 있다)")
        return
    created = [path for path in (marker_home / MARKER_DIRS[name][0], base) if not path.exists()] + [folder]
    for path in created:
        path.mkdir()
    (folder / "SKILL.md").write_text(
        f"---\nname: {MARKER}\ndescription: acp-starter 격리 확인용 표시다. 이 이름이 보이면 개인 스킬이 새어 든 것이다.\n---\n"
        "표시용 스킬이다. 아무 일도 하지 않는다.\n", encoding="utf-8")
    client = engines.make(name, workspace, preamble=preamble)
    try:
        client.start()
        result = ask(client, "지금 네가 쓸 수 있는 스킬(skill)의 이름을 모두 쉼표로 나열한다. 하나도 없으면 '없음'이라고만 답한다.")
        leaked = MARKER in result.text
        report.say(f"- 개인 스킬 격리({base}): {'새어 듦 ✗' if leaked else '막힘 ✓'}")
        report.say(f"    답: {one_line(result.text)}")
    except Exception as error:  # 오류를 기록하고 표시용 스킬은 반드시 지운다
        report.say(f"- 개인 스킬 격리: 오류 {type(error).__name__}: {error}")
    finally:
        client.close()
        (folder / "SKILL.md").unlink(missing_ok=True)
        for path in reversed(created):
            try:
                path.rmdir()
            except OSError:
                pass


# ---- 시작 ----

def main():
    parser = argparse.ArgumentParser(description="my-agent-platform Windows 확인")
    parser.add_argument("repo", nargs="?", default="", help="my-agent-platform 폴더. 빼면 이 스크립트 옆의 my-agent-platform")
    parser.add_argument("--real", action="store_true", help="로그인된 엔진을 실제로 짧게 돌린다(사용량이 조금 든다)")
    parser.add_argument("--engines", default="", help="--real에서 볼 엔진만 쉼표로. 예: claude,codex")
    parser.add_argument("--marker", choices=("ask", "yes", "no"), default="ask", help="개인 스킬 격리 확인")
    parser.add_argument("--marker-home", default="", help=argparse.SUPPRESS)   # 개발용: 표시용 스킬을 둘 다른 폴더
    args = parser.parse_args()

    here = pathlib.Path(__file__).resolve().parent
    repo = pathlib.Path(args.repo).resolve() if args.repo else here.parent / "my-agent-platform"
    if not (repo / "dashboard.py").is_file():
        print(f"my-agent-platform 폴더를 찾지 못했다: {repo}")
        print("폴더를 적어서 다시 실행한다: python windows_test\\windows_check.py C:\\work\\레포\\my-agent-platform")
        sys.exit(2)

    name = "windows_check_실제엔진.txt" if args.real else "windows_check_기본.txt"
    report = Report(here / name)
    report.say(f"# my-agent-platform Windows 확인 ({'실제 엔진' if args.real else '기본'})")
    report.say("")
    sys.path.insert(0, str(repo))
    started = time.time()
    try:
        check_environment(report, repo)
        if not args.real:
            check_unit_tests(report, repo)
        import custom_loader
        import engines
        states = check_engines(report, engines)
        if args.real:
            marker = args.marker
            if marker == "ask":
                answer = input("개인 스킬 격리도 확인할까요? 사용자 폴더의 .kiro\\skills, .claude\\skills, .agents\\skills에 "
                               f"'{MARKER}' 폴더를 잠깐 만들었다가 지웁니다. [y/N] ")
                marker = "yes" if answer.strip().lower() in ("y", "yes", "예", "ㅛ") else "no"
            marker_home = (pathlib.Path(args.marker_home) if args.marker_home else pathlib.Path.home()) if marker == "yes" else None
            only = {item.strip() for item in args.engines.split(",") if item.strip()}
            check_real(report, engines, custom_loader, repo, states, only, marker_home)
    except KeyboardInterrupt:
        report.say("- 사람이 멈췄다(Ctrl+C).")
    except Exception as error:  # 스크립트 자체의 오류도 결과 파일에 남긴다
        report.say(f"- 확인 스크립트 오류: {type(error).__name__}: {error}")
        for line in traceback.format_exc().splitlines():
            report.say("    " + line)
    report.say(f"걸린 시간: {time.time() - started:.0f}초")
    report.save()
    print("")
    print(f"끝. 결과 파일: {report.path}")
    print("이 파일을 커밋하고 푸시한다: git add windows_test && git commit -m \"test: Windows 확인 결과\" && git push")


if __name__ == "__main__":
    main()
