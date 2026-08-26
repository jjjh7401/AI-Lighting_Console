# t111 — 이름 안의 제어문자를 계획 단계에서 거절한다

- 카드: t111 (C6, 외부 감사 2026-08-26)
- 브랜치: `WT-label-control-chars` · 워크트리 `.claude/worktrees/t111`
- 기준: `origin/main` `94d4f76` 에서 새로 뗀 트리
- 커밋: `b56dadf`
- 실기: **0건** — 순수 검증 카드. 콘솔·네트워크 접촉 없음

## 1. 주장 (Claim)

`server/presets/store.py` 의 `preset_label_refusal` 이 이름 **안**의 제어문자를
거절한다. 그래서 t97 이 세운 원칙 「못 보내는 이름을 계획에 싣지 않는다」가
따옴표를 넘어 제어문자까지 걸린다.

## 2. 증거 (Evidence)

### 2.1 착수 전 실측 — 수정 전 트리에서 잰 값

    preset_label_refusal("쇼\n하이")  -> None     (보낼 수 있다고 답한다)
    preset_label_refusal("쇼\t하이")  -> None
    preset_store_commands(1, 7, "쇼\n하이")
      -> ('Store Preset 1.7', "Label Preset 1.7 '쇼\n하이'")   터지지 않는다
    parse_preset_csv 탭 맨몸 필드     -> ['쇼\t하이']
    parse_preset_csv 개행 따옴표 필드 -> ['쇼\n하이']

end-to-end (`import_lxseq_presets`, 기록형 포트):

    preview  planned = [쓰지, 탭\t이름]   held = []
    apply    approval.asked 에 "Label Preset 1.2 '탭\t이름'" 이 올라간다
             port.executed 에도 같은 줄이 실린다

따옴표(t97)는 빌더에서 터졌지만 제어문자는 빌더·계획·승인을 전부 통과했다.

### 2.2 수정 후

- 새 검사 15건 통과 (`server/tests/test_lxseq_preset_control_char_names.py`)
- 전체 스위트 `uv run pytest -q` → **10411 passed, 12 skipped**, 165s
- `ruff check` / `ruff format --check` → clean

### 2.3 뮤테이션 — 7/7 KILLED

매 회 치환 적용을 단언했고(`assert mutated != ORIGINAL`), 복원은 백업+sha256
체크섬으로 했다(`git checkout` 안 씀).

    KILLED  M1 갈래 통째 제거                     9 failed
    KILLED  M2 범주를 Cc 로만 좁힘                2 failed
    KILLED  M3 범주를 Zl/Zp 로만 좁힘             9 failed
    KILLED  M4 ord(ch) < 32 로 대체 (문법층 흉내) 2 failed
    KILLED  M5 판정 대상을 strip 전 label 로      2 failed
    KILLED  M6 조건 뒤집기 (not in)               7 failed
    KILLED  M7 빌더 문면을 옛 거짓 문면으로       1 failed

M4 가 판별력의 핵심이다 — 문법층과 같은 `ord(ch) < 32` 로 좁히면 DEL·NEL·
U+2028 항목이 빨개진다. M5 는 경계 축이다 — 판정을 `strip` 전으로 옮기면
바깥 공백 이름이 잘못 거절돼 양성 대조군이 빨개진다.

## 3. 기준선 귀속 (Baseline-attribution)

    git log --oneline -1 origin/main   -> 94d4f76 (t109 #168 머지분)
    git rev-parse --show-toplevel      -> .claude/worktrees/t111
    uv sync --group dev                -> 이 트리 자체 .venv (주 체크아웃 안 빌림)

모든 수치는 이 트리, 이 커밋(`b56dadf`)에서 이 세션이 실행해 관측한 값이다.
옮겨 온 값 없음.

## 4. 카드 전제 정정 2건 (둘 다 실측)

### 4.1 「2·3차 방어가 산다」는 C0 에만 참이다

    validate("Label Preset 1.2 '탭\t이름'") -> ok=False  control character
    validate("Label Preset 1.2 '탭\n이름'") -> ok=False  must be a single line
    validate("Label Preset 1.2 '쓰지'")     -> ok=True            (양성 대조군)
    validate("... 'a" + chr(0x7f) + "b'")   -> ok=True   DEL   통과
    validate("... 'a" + chr(0x85) + "b'")   -> ok=True   NEL   통과
    validate("... 'a" + chr(0x2028) + "b'") -> ok=True   U+2028 통과

안전 문법층은 `ord(ch) < 32` 로만 거른다. 프로토콜층(`_validate_rest`)은
겹따옴표와 `\n`·`\r` 만 본다. 따라서 DEL·C1·U+2028 에는 **이 술어가 유일한
방어**다. 이 수정이 그 자리를 덮는다 — Cc 는 0x7F·C1 을, Zl/Zp 는 U+2028·
U+2029 를 포함한다.

문법층 자체를 넓히는 것은 이 카드 범위가 아니다(다른 파일 · 후속 카드).

### 4.2 거절이 일어나는 정확한 자리는 안전 게이트다

카드는 「발사 시점에 거부」라고 적었다. 실측으로 좁히면: 빌더도 프로토콜도
아니고 `server/safety/gate.py` 의 `validate` 호출이다. 개행 이름은 빌더를
통과하고 승인 화면까지 올라간 뒤 거기서 멈춘다.

## 5. 결함 계열 전수표 — 넓히지 않고 보고만 한다

카드는 「술어가 하나라 수정 지점도 하나다」라고 했다. **t111 축에선 참이다** —
`preset_label_refusal` 을 부르는 곳은 `store.py` 자신과 `lxseq/preset_mapper.py`
둘뿐이다(grep 확인). 그러나 같은 규칙(`not text or "'" in text or '"' in text`)의
**사본**이 술어 밖에 5자리 있고, 전부 같은 구멍을 갖는다.

텍스트 추론이 아니라 **호출로** 확인했다(`탭\t이름` 을 넣고 산출물을 읽음):

    EMITTED  pointing.position_preset_store_commands  "Label Preset 2.7 '탭\t이름'"
    EMITTED  pointing.position_cue_store_commands     "Store Sequence 11 Cue 1 '탭\t이름'"
    EMITTED  position_fx._validated_label             '탭\t이름'
    EMITTED  session._phaser_sequence_commands        "Store Sequence 11 Cue 1 '탭\t이름' CueFade 2"
    EMITTED  store.preset_apply_command(attribute)    "Group 1 ; Attribute '탭\t이름' At 50"

5자리 모두 기형 명령을 조립한다 — **검증된 코드 사실**이다.

**안 잰 것**: 각 자리에 사용자 제어 제어문자가 **도달하는지**는 안 쟀다.
`preset_apply_command` 의 attribute 는 코드 상수로 보이고, 나머지 넷은 툴 인자
경로라 도달이 그럴듯하지만 관측하지 않았다. 도달을 재기 전에 「결함 5건」이라
부르면 그게 미관측 결함 주장이다. 그래서 **넓히지 않았다** — 후속 카드 재료다.

## 6. 안 잰 것 (Gaps) — 이게 결론을 흔드나 / 다른 축인가

| 안 잰 것 | 결론을 흔드나 |
|---|---|
| 실기 0건 — 콘솔에 안 쐈다 | **다른 축.** 이 카드는 계획-발사 불일치를 고친다. 콘솔 접촉이 없어야 맞다 |
| 형제 5자리의 **도달** 여부 | **다른 축.** t111 축(프리셋 라벨)의 판정에는 무관 |
| 문법층이 DEL·C1·U+2028 을 통과시키는 것의 **무대 영향** | **다른 축.** 이 수정이 계획 단계에서 덮는다. 문법층 수정은 별개 카드 |
| 안전 게이트가 승인 **전**인지 **후**인지 | **흔들지 않는다.** 어느 쪽이든 그 런이 멈춘다는 사실은 같다. 다만 「승인 화면에 기형 명령이 뜬다」는 4.2 서술의 정확도는 이 축에 걸린다 |
| U+2029(Zp) 는 검사에 안 넣었다 | **흔들지 않는다.** Zl 과 같은 범주 분기라 구조적으로 같이 걸린다. 다만 자리별로 쏘진 않았다 |

## 7. 잔여 위험 (Residual-risk)

- 이 수정은 **거절을 넓힌다**. 안쪽 제어문자를 일부러 쓰던 시트가 있었다면 이제
  `held` 로 떨어진다. 양성 대조군(안쪽 공백·문장부호·바깥 공백)으로 과잉 거절을
  막았지만, 실제 쇼파일 코퍼스로는 안 재 봤다.
- 빌더 문면이 바뀌었다(`rejected: <이유>`). 그 문면을 파싱하는 소비자가 있다면
  깨진다 — 저장소 안에는 없다(grep 확인).
- CI 는 머지 결과를 잰다. 이 트리의 초록이 머지 후 초록을 보증하지 않는다.
