# Windows 확인

`my-agent-platform/`이 Windows에서 도는지 확인하는 순서입니다. 이 폴더는 확인용이고, 학생 레포에는 넣지 않습니다.

## 준비

- Python 3.10 이상, Git, Kiro CLI(`kiro-cli login`까지)
- Claude나 Codex 엔진도 볼 때만: Node.js 22 이상, `claude` 또는 `codex` 명령

## 순서

레포를 받은 폴더의 PowerShell에서 실행합니다.

```
git clone https://github.com/nxtcloud-edu/kmu-2026-ai-agent-class-00.git
cd kmu-2026-ai-agent-class-00
```

1. 기본 확인을 실행합니다. 엔진을 부르지 않습니다. 1~3분 걸립니다.

   ```
   python windows_test\windows_check.py
   ```

2. 앱을 켜고 `시작하기.html`의 4번부터 따라 합니다. 확인한 것을 `결과_기록표.txt`에 적습니다.

   ```
   cd my-agent-platform
   python dashboard.py
   ```

3. 앱을 끄고(Ctrl+C) 레포 폴더로 돌아와서 실제 엔진 확인을 실행합니다. 로그인된 엔진마다 짧은 질문 4개를 보냅니다.

   ```
   cd ..
   python windows_test\windows_check.py --real
   ```

4. 결과를 올립니다.

   ```
   git add windows_test
   git commit -m "test: Windows 확인 결과"
   git push
   ```

## 결과 파일

| 파일 | 내용 |
|---|---|
| `windows_check_기본.txt` | 환경, 도구의 버전, 단위 테스트, 엔진의 설치와 로그인 상태 |
| `windows_check_실제엔진.txt` | 엔진마다 인사, 명령 실행, 파일 쓰기(허락), 파일 쓰기(거절), 끈 뒤에 남은 프로세스 |
| `결과_기록표.txt` | 앱 화면에서 손으로 확인한 것 |

화면에 오류가 나오면 그 글을 `결과_기록표.txt`의 메모에 그대로 붙여 넣습니다.
