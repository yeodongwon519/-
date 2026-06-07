# 🎬 Claude Premiere Bridge

Claude Code ↔ Adobe Premiere Pro 실시간 연동 브리지 (Windows / Premiere 2024·2025).

Claude Code가 작성한 ExtendScript 명령을 프리미어가 **자동으로 실행**하고,
결과를 다시 파일로 돌려주어 "지시 → 자동 편집 → 결과 확인" 루프를 만듭니다.

```
[내 PC의 Claude Code]
   │  .jsx 명령 파일 작성
   ▼
~/ClaudePremiereBridge/commands/        ← (1초마다 감시)
   │
   ▼
[프리미어 안의 브리지 패널]  ── evalScript ──▶  실제 편집 적용
   │  결과 기록
   ▼
~/ClaudePremiereBridge/results/         ← Claude Code가 읽음
```

> `~` 는 Windows에서 `C:\Users\<내계정>` 입니다.

---

## 설치 (한 번만)

### 0. Claude Code를 내 PC에 설치
지금 쓰고 있는 웹/클라우드 세션은 **내 PC의 프리미어에 닿을 수 없습니다.**
실제 연동은 PC에 설치한 Claude Code(터미널 CLI 또는 데스크톱 앱)에서 해야 합니다.
- 설치: https://code.claude.com/docs

### 1. 디버그(미서명 확장) 허용
`enable-debug-mode.reg` 를 더블클릭 → "예" → 확인.
(레지스트리에 `PlayerDebugMode=1` 을 넣어 서명 안 된 패널을 허용합니다.)

### 2. 패널 설치
이 `premiere-bridge` 폴더를 통째로 아래 경로에 복사합니다.
폴더 이름은 `com.claude.premierebridge` 로 바꿔주세요.

```
C:\Users\<내계정>\AppData\Roaming\Adobe\CEP\extensions\com.claude.premierebridge\
```

복사 후 구조:
```
...\extensions\com.claude.premierebridge\
   ├─ CSXS\manifest.xml
   ├─ client\index.html
   ├─ client\js\main.js
   └─ host\index.jsx
```

### 3. 프리미어에서 패널 열기
프리미어를 **완전히 종료 후 재시작** → 메뉴 `창(Window) > 확장(Extensions) > Claude Premiere Bridge`.
패널에 **"감시 중 (실행 대기)"** 초록 표시가 뜨면 성공입니다.
`연결 테스트` 버튼을 누르면 `Premiere 25.x 연결 OK` 가 로그에 보여야 합니다.

---

## 사용법

### 명령 보내기
`~/ClaudePremiereBridge/commands/` 폴더에 `.jsx` 파일을 하나 떨어뜨리면 끝.
- 파일 이름은 아무거나 (예: `cmd_001.jsx`). **타임스탬프/번호 순으로 실행**됩니다.
- 파일의 **마지막 표현식 값**이 결과로 저장됩니다.
- 실행된 명령은 `*.jsx.done` 으로 이름이 바뀝니다(중복 실행 방지).

### 결과 받기
`~/ClaudePremiereBridge/results/<같은이름>.json`:
```json
{
  "command": "cmd_001.jsx",
  "ok": true,
  "result": "Premiere 25.0 연결 OK",
  "time": "2026-06-07T11:40:00.000Z"
}
```

### Claude Code에게 시키는 법 (PC에서)
> "intro.mp4 를 V1 트랙 5초 지점에 넣고, 그다음 타임라인 상태 알려줘"

→ Claude가 `commands/` 에 `.jsx` 를 쓰고 → 패널이 실행 → `results/` 의 JSON을 Claude가 읽어 보고합니다.

`examples/` 폴더에 바로 쓸 수 있는 명령 예제가 있습니다.

---

## 미리 만들어진 헬퍼 함수 (`host/index.jsx`)

명령 안에서 바로 호출할 수 있습니다. (직접 `app.*` API를 써도 됩니다.)

| 함수 | 설명 |
|------|------|
| `ppVersion()` | 프리미어 버전 (연결 확인) |
| `ppActiveSequence()` | 현재 활성 시퀀스 이름 |
| `ppListProjectItems()` | 프로젝트 모든 항목 이름 |
| `ppSequenceInfo()` | 활성 시퀀스 트랙/클립 구조(JSON) |
| `ppSeek(초)` | 재생헤드 이동 |
| `ppInsertClip(이름, 초, 트랙)` | 클립을 비디오 트랙에 삽입 |
| `ppFindItem(이름)` | 이름으로 프로젝트 항목 찾기 |
| `ppSave()` | 프로젝트 저장 |

필요한 편집 동작이 생기면 `host/index.jsx` 에 함수를 추가하면 됩니다.
(프리미어 ExtendScript API 레퍼런스: https://ppro-scripting.docsforadobe.dev/ )

---

## 문제 해결

| 증상 | 해결 |
|------|------|
| 패널 메뉴가 안 보임 | 1) `.reg` 적용 확인 2) 폴더 경로/이름 확인 3) 프리미어 재시작 |
| 패널은 뜨는데 "감시" 안 됨 | manifest의 `--enable-nodejs` 가 있어야 함(이 저장소엔 포함됨). CEP 버전 불일치면 빈 패널이 뜸 |
| `연결 테스트` 무응답 | 프리미어에 **프로젝트를 하나 열어둔 상태**에서 시도 |
| 명령이 실행 안 됨 | `commands/` 폴더 경로 확인, 파일 확장자가 `.jsx` 인지 확인 |
| 결과가 `ok:false` | `result` 의 에러 메시지 확인. ExtendScript 문법/존재하지 않는 클립명 등 |

---

## 보안 메모
이 브리지는 `commands/` 폴더에 들어온 ExtendScript를 **그대로 실행**합니다.
이 폴더에 Claude Code 외 다른 프로그램이 쓰지 못하도록 관리하세요.
