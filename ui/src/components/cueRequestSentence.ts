// PLAN CUE 수정요청 생성기 — 선택 → 문장 조립 (t460, SPEC-LDDESIGN-001 REQ-087~095,
// REQ-100~101). 순수 함수만 있다(REACT 없음, 콘솔에 아무것도 안 보낸다).
//
// REQ-092: 이 파일은 서버 파서(`server/design/cue_sheet_edit.py`
// `parse_cue_sheet_edit_request`)를 흉내 내거나 우회하지 않는다 — 그 파서가
// 이미 읽는 한국어 어휘로 "문장"만 만든다. 판정·거절 사유는 언제나 서버
// 응답(REQ-092)이다. 이 파일이 만드는 문장이 파서가 읽는 어휘와 어긋나면
// AC-LDDESIGN-039(pytest 어휘 일치 시험)가 잡는다.
//
// 그룹 스코프 가능 항목은 셋뿐이다(`cue_sheet_edit.py` `_GROUP_SCOPED_FIELDS`
// 그대로): intensity·intensity_delta·palette_primary. 나머지(무브먼트·
// 이펙트·페이드·전환)는 큐 전체 값이다(REQ-089) — GeneratorChange 타입에서
// 그룹을 아예 받지 않는 걸로 이 제약을 코드로 고정한다.

/** 조도(밝기) 지정 — 그룹 다중 선택 가능(REQ-088). `groups` 가 없거나 빈
 * 배열이면 큐 전체(형태 없는 구간이거나 전 그룹 지정)다. */
export interface IntensityChange {
  field: "intensity";
  groups: string[] | null;
  /** 0~100 — 위 상·하한 힌트일 뿐 최종 판정은 서버다(REQ-092). */
  value: number;
  /** 표시용 "이전" 값 — 서버 값 그대로거나 "혼합"(REQ-088). */
  before: string;
}

/** 컬러(주) 지정 — 그룹 정확히 하나(KEY 또는 BACK, `cue_sheet_edit.py`
 * `_GROUP_COLOR_FIELD`). 컬러는 REQ-089상 그룹 스코프 항목이라 큐 전체
 * 컬러는 이 생성기가 만들지 않는다(자유 입력 한 줄로만 가능, REQ-101). */
export interface ColorChange {
  field: "palette_primary";
  groups: [string];
  /** 파서가 그대로 받는 색 이름 — 프리셋 번호가 아니다(팔레트 명이지,
   * console 프리셋과는 다른 어휘 — REQ-089는 무브먼트·이펙트·컬러·딤머
   * 프리셋 반영 값 패널에 대한 규정이고, 이 필드는 파서의 컬러 문장이다). */
  value: string;
  before: string;
}

/** 무브먼트 — 큐 전체(REQ-089). 값은 프리셋 이름 문자열. */
export interface MovementChange {
  field: "movement";
  value: string;
  before: string;
}

/** 이펙트 — 큐 전체(REQ-089). 값은 프리셋 이름 문자열. */
export interface EffectChange {
  field: "effect";
  value: string;
  before: string;
}

/** 페이드 — 큐 전체. 초 단위, 서버 상한 60초(cue_sheet_edit.py `_FADE_MAX_SECONDS`,
 * 힌트로만 보여준다 — 최종 판정은 서버). */
export interface FadeChange {
  field: "fade_seconds";
  value: number;
  before: string;
}

/** 전환 — 큐 전체. `cue_sheet_edit.py` `TRANS_VALUES` 3종뿐이다. */
export interface TransChange {
  field: "trans";
  value: "SNAP" | "XFADE" | "FADE";
  before: string;
}

/** t466/t470 — 트래킹. 큐 전체(REQ-089). `cue_sheet_edit.py`
 * `TRACKING_VALUES` 4종뿐이다. */
export interface TrackingChange {
  field: "tracking";
  value: "Track" | "Block" | "Cue Only" | "Release";
  before: string;
}

/** t466/t470 — MIB. 큐 전체(REQ-089). `cue_sheet_edit.py` `MIB_MODES` 4종뿐이다
 * — 조립기가 계산한 기존 `mib`(참/거짓)와는 다른 칸이다. */
export interface MibChange {
  field: "mib_mode";
  value: "none" | "dark" | "mark" | "live";
  before: string;
}

/** t466/t470 — 페이저. 큐 전체(REQ-089). 값은 프리셋 이름(딤머 풀 1 또는
 * 컬러 풀 4에서 고른다 — 어느 풀이든 값은 이름 문자열 하나). */
export interface PhaserChange {
  field: "phaser";
  value: string;
  before: string;
}

/** t466/t470 — 포지션. 큐 전체(REQ-089). 값은 프리셋 이름 + 번호(풀 2만,
 * "2.<point>" 형태) — t460 이 임시로 쓰던 `movement` 문장을 이 필드가
 * 대체한다(포지션 행 전용). */
export interface PositionChange {
  field: "position";
  value: string;
  presetNo: string;
  before: string;
}

export type GeneratorChange =
  | IntensityChange
  | ColorChange
  | MovementChange
  | EffectChange
  | FadeChange
  | TransChange
  | TrackingChange
  | MibChange
  | PhaserChange
  | PositionChange;

/** 변경 스택 한 항목 — 화면 표시·전송 순서 유지를 위한 안정적 id. */
export interface GeneratorChangeItem {
  id: string;
  change: GeneratorChange;
}

function groupPrefix(groups: string[] | null | undefined): string {
  return groups && groups.length > 0 ? `${groups.join("·")} ` : "";
}

// t470 — 트래킹·MIB는 닫힌 4택이라(server TRACKING_VALUES·MIB_MODES) 값마다
// 받침 유무가 고정돼 있다. 파서 정규식(`_SET_TAIL`)은 "으로"·"로" 둘 다
// 받으므로(어느 쪽을 써도 판정은 갈리지 않는다) 문법적으로 자연스러운 쪽을
// 표에 직접 박는다 — 일반 한글 받침 알고리즘은 영문 프리셋 이름(포지션·
// 페이저)까지 일반화할 수 없어 짓지 않는다(기존 무브먼트/이펙트 필드처럼
// "로" 고정이 그 두 칸의 방식이다).
const TRACKING_PARTICLE: Record<TrackingChange["value"], "으로" | "로"> = {
  Track: "으로", // 트랙 — 받침 ㄱ
  Block: "으로", // 블록 — 받침 ㄱ
  "Cue Only": "로", // 큐온리 — 받침 없음
  Release: "로", // 릴리즈 — 받침 없음
};

// MIB 표시 라벨 — 서버 `_mib_label`과 같은 규칙("none"만 "없음"으로 보인다).
const MIB_LABEL: Record<MibChange["value"], string> = {
  none: "없음",
  dark: "dark",
  mark: "mark",
  live: "live",
};

const MIB_PARTICLE: Record<MibChange["value"], "으로" | "로"> = {
  none: "으로", // 없음 — 받침 ㅁ
  dark: "로", // 다크 — 받침 없음
  mark: "로", // 마크 — 받침 없음
  live: "로", // 라이브 — 받침 없음
};

/** 선택 하나 → 파서가 읽는 한 문장. 큐 번호는 `_CUE_NUMBER`/`_CUE_ANCHOR`가
 * 요구하는 지시어("큐 N")를 그대로 건다 — cue_selected 지름길(t290)에
 * 기대지 않는다(생성기는 화면에서 큐를 이미 골랐어도 명시적으로 적는다,
 * 짧은 문장 판별기의 우연에 기대지 않기 위해서다). */
export function cueRequestSentence(cueNumber: number, change: GeneratorChange): string {
  switch (change.field) {
    case "intensity":
      return `큐 ${cueNumber} ${groupPrefix(change.groups)}밝기 ${change.value}%로 바꿔줘`;
    case "palette_primary":
      return `큐 ${cueNumber} ${change.groups.join("·")} 컬러 ${change.value}로 바꿔줘`;
    case "movement":
      return `큐 ${cueNumber} 무브먼트 ${change.value}로 바꿔줘`;
    case "effect":
      return `큐 ${cueNumber} 이펙트 ${change.value}로 바꿔줘`;
    case "fade_seconds":
      return `큐 ${cueNumber} 페이드 ${change.value}초로 바꿔줘`;
    case "trans":
      return `큐 ${cueNumber} 전환을 ${change.value}로 바꿔줘`;
    case "tracking":
      return `큐 ${cueNumber} 트래킹 ${change.value}${TRACKING_PARTICLE[change.value]} 바꿔줘`;
    case "mib_mode":
      return `큐 ${cueNumber} MIB ${MIB_LABEL[change.value]}${MIB_PARTICLE[change.value]} 설정`;
    case "phaser":
      return `큐 ${cueNumber} 페이저 ${change.value}로 바꿔줘`;
    case "position":
      return `큐 ${cueNumber} 포지션 ${change.presetNo} ${change.value}로 바꿔줘`;
  }
}

/** 변경 스택 diff 줄 라벨 — REQ-091 "~ 필드 이전값 → 이후값" 형식. */
export function cueRequestDiffLabel(change: GeneratorChange): string {
  switch (change.field) {
    case "intensity":
      return `~ ${groupPrefix(change.groups)}밝기 ${change.before} → ${change.value}%`;
    case "palette_primary":
      return `~ ${change.groups.join("·")} 컬러 ${change.before} → ${change.value}`;
    case "movement":
      return `~ 무브먼트 ${change.before} → ${change.value}`;
    case "effect":
      return `~ 이펙트 ${change.before} → ${change.value}`;
    case "fade_seconds":
      return `~ 페이드 ${change.before} → ${change.value}초`;
    case "trans":
      return `~ 전환 ${change.before} → ${change.value}`;
    case "tracking":
      return `~ 트래킹 ${change.before} → ${change.value}`;
    case "mib_mode":
      return `~ MIB ${change.before} → ${MIB_LABEL[change.value]}`;
    case "phaser":
      return `~ 페이저 ${change.before} → ${change.value}`;
    case "position":
      return `~ 포지션 ${change.before} → ${change.presetNo} ${change.value}`;
  }
}

/** REQ-091/101 — 변경 스택 전체를 순차 전송할 문장 배열로 조립한다. 자유
 * 입력(REQ-101)은 **마지막** 문장 끝에 그대로(해석 없이) 덧붙는다. 선택된
 * diff 항목이 하나도 없으면 자유 입력만으로는 아무 것도 보내지 않는다
 * (AC-053의 전제 "선택된 diff 항목 1개 이상"과 같다 — 이 생성기는 큐시트
 * 편집 문장만 다룬다, 순수한 잡담 라우팅은 이 경로의 일이 아니다). */
export function buildCueRequestSentences(
  cueNumber: number,
  items: GeneratorChangeItem[],
  freeText: string,
): string[] {
  const sentences = items.map((item) => cueRequestSentence(cueNumber, item.change));
  const trimmedFree = freeText.trim();
  if (trimmedFree && sentences.length > 0) {
    const lastIndex = sentences.length - 1;
    sentences[lastIndex] = `${sentences[lastIndex]} ${trimmedFree}`;
  }
  return sentences;
}

/** REQ-088 — 선택된 그룹들의 조도가 서로 다르면 "혼합"(단일 축 차이).
 * 하나도 없으면(그룹 미선택) EMPTY. */
export function mixedIntensityLabel(levels: number[]): string {
  if (levels.length === 0) return "—";
  const unique = Array.from(new Set(levels));
  return unique.length === 1 ? `${unique[0]}%` : "혼합";
}

/** REQ-088 — 선택된 그룹들의 색이 서로 다르면 "혼합 2색"(그 이상이면
 * "혼합 N색") — 색상 차이는 밝기 차이("혼합")와 다른 라벨을 쓴다. */
export function mixedColorLabel(colors: (string | undefined)[]): string {
  const known = colors.filter((color): color is string => Boolean(color));
  if (known.length === 0) return "—";
  const unique = Array.from(new Set(known));
  if (unique.length === 1) return unique[0];
  return `혼합 ${unique.length}색`;
}
