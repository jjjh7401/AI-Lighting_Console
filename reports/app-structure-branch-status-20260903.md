# AI-Lighting_Console 구조 및 워크트리 상태 리포트 — 2026-09-03

## 결론

- 메인 워크트리 `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console` 는 `main` 브랜치이며 `git status --short --branch` 기준 staged/unstaged/untracked 모두 0이다.
- 모든 워크트리와 브랜치가 `main`에 머지된 상태는 아니다.
- 닫아도 안전하다고 확인된 로컬 worktree branch는 `WT-rig-coords` 뿐이다. `jjjh7401/blocked16`, `jjjh7401/LX-SEQ`는 `main`에 없는 커밋이 있다.

## Git 확인 결과

| 항목 | 상태 | 근거 |
|---|---:|---|
| main working tree | clean | `branch main...origin/main`, staged 0, unstaged 0, untracked 0 |
| worktree count | 4 | `git worktree list --porcelain` |
| merged local branches | 2 | `main`, `WT-rig-coords` |
| unmerged local branches | 2 | `jjjh7401/blocked16`, `jjjh7401/LX-SEQ` |
| unmerged remote branches | 21 | `git branch -r --no-merged main` |

### Local worktrees

| Path | Branch | HEAD | Merge status vs main | main...branch counts |
|---|---|---|---|---|
| `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console` | `main` | `adae0ac` | current main | — |
| `.claude/worktrees/t210-fire` | `WT-rig-coords` | `aba50f1` | merged into main | 78 behind / 0 ahead |
| `/Users/studiox/orca/workspaces/AI-Lighting_Console/blocked16` | `jjjh7401/blocked16` | `363d28f` | not merged | 326 behind / 6 ahead |
| `/Users/studiox/orca/workspaces/AI-Lighting_Console/LX-SEQ` | `jjjh7401/LX-SEQ` | `49c235a` | not merged | 294 behind / 28 ahead |

## 앱 구조

이 앱은 grandMA3 조명 콘솔을 한국어 자연어로 제어하는 데스크톱/웹 하이브리드 앱이다.

```text
React/Vite UI ↔ FastAPI WebSocket/REST ↔ ChatSession ↔ Orchestrator ↔ LLM provider
                                      ↘ SafetyGate ↔ OSC ↔ grandMA3 Lua responder
```

### 주요 런타임 경로

1. 사용자가 `ui`에서 한국어 지시를 보낸다.
2. `server/web/app.py`의 `/ws`가 protocol v1 메시지를 받는다.
3. `ChatSession`이 한 지시 단위의 상태, 첨부, 승인, 질문, 타임라인을 관리한다.
4. `Orchestrator`가 LLM provider와 tool loop를 돈다. 기본 루프 한도는 24 model calls, self-correction은 최대 3회다.
5. 콘솔로 나가는 명령은 `SafetyGate`를 반드시 통과한다.
6. `bridge/protocol.py`가 Lua responder 호출/응답 포맷을 만들고 해석한다.
7. grandMA3의 `console/lua/copilot_responder.lua`가 `/copilot/state`, `/copilot/feedback`로 응답한다.

## 폴더 구조

```text
AI-Lighting_Console/
├─ ui/                         React 18 + Vite Korean chat/control UI
│  ├─ src/App.tsx              split-pane shell, chat, dashboard, approvals
│  ├─ src/useCopilotSocket.ts  WebSocket client hook
│  ├─ src/protocol.ts          protocol v1 client schema/parsers
│  ├─ src/components/          cards, dashboard, timeline, settings, paperwork
│  └─ public/                  copied user guide and static UI assets
├─ server/                     Python FastAPI + orchestration backend
│  ├─ web/                     /ws, /healthz, REST APIs, session bridge
│  ├─ orchestrator/            model ↔ tool loop and MA3 tool registry
│  ├─ safety/                  command grammar/risk/approval chokepoint
│  ├─ bridge/                  OSC/responder wire protocol codec
│  ├─ llm/                     Anthropic, Gemini, Claude Code, Ollama adapters
│  ├─ spatial/                 pointing, choreography, presets, topology
│  ├─ lxseq/                   LX-SEQ parsers/mappers/cue and preset builders
│  ├─ vwx/                     Vectorworks/MVR import, address fit, patch plan
│  ├─ prechk/                  pre-show/channel/patch/inventory checks
│  ├─ deploy/                  Lua plugin compile/scan/review/deploy pipeline
│  ├─ paperwork/               generated cue/preset/patch paperwork
│  ├─ presets/, rig/, sheets/  pool reads, rig paging, sheet registry
│  └─ tests/                   Python behavior/contract tests
├─ console/lua/                grandMA3 CopilotResponder plugin and protocol
├─ src-tauri/                  Tauri v2 macOS shell bundling ui/dist + backend
├─ packaging/                  sidecar staging, signing, DMG/app verification
├─ src/Lighting_Designer/      sample rig packs, specs, MA3 outputs, build tools
├─ docs/, handoff/, reports/   user guides, runbooks, handoffs, report artifacts
├─ config/provider.toml        active LLM provider/model config, no credentials
├─ pyproject.toml, uv.lock     Python package and pinned dependency set
└─ package.json                root shell/build/test scripts
```

## 기술 스택

| 영역 | 기술 |
|---|---|
| Desktop shell | Tauri v2, macOS app/DMG bundle |
| Frontend | React 18.3.1, TypeScript 5.6, Vite 5.4, Vitest |
| Backend | Python 3.11+, FastAPI, uvicorn, websockets |
| Console transport | OSC, Python `python-osc`, grandMA3 Lua plugin |
| LLM providers | Anthropic, Gemini, Claude Code, Ollama |
| Packaging | PyInstaller-style sidecar staging, Tauri externalBin, codesign/DMG scripts |
| Tests | 264 Python test files, 21 UI test files observed |

## 다음 작업 판단

- `main`에서 다음 작업을 진행하는 것은 가능하다. 메인 워크트리는 깨끗하다.
- “모두 닫기”는 아직 안전하다고 볼 수 없다. `blocked16`과 `LX-SEQ`는 main에 없는 커밋이 각각 6개, 28개 있다.
- `WT-rig-coords`는 main 기준 ahead 0이라 정리 후보지만, 실제 삭제 전에는 그 worktree의 working tree clean 여부를 별도로 확인해야 한다.
