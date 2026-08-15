# IMGLAYOUT-001 병렬 슬라이스 계약 (M1/M2/M3 공유 — 변경 금지, 변경 필요 시 코디네이터에 ask)

## 1. WS 메시지 (M1 소유, M3·M4가 소비)

클라이언트→서버, `server/web/messages.py` + `ui/src/protocol.ts` 양쪽 등록:

```json
{"v": 1, "type": "layout_image_upload",
 "file_name": "stage-sketch.png",
 "mime_type": "image/png",
 "content_base64": "..."}
```

- 허용 MIME: `image/png` `image/jpeg` `image/webp`
- 상한: 디코드 후 5,242,880 바이트 (5MB)
- 서버 세션 보관 필드명: `LayoutImageUpload(file_name: str, mime_type: str, content_base64: str)`
  — 세션 속성 `self._layout_image: LayoutImageUpload | None` (최신 1장만, 새 업로드가 교체)
- 성공 응답: 기존 `notice` 이벤트 (`"이미지 '<file_name>' 첨부됨 (<n>KB)"`)
- 실패 응답: 기존 `error` 이벤트, kind="layout_image_rejected"
- UI 빌더 함수명: `buildLayoutImageUpload(fileName, mimeType, contentBase64)`

## 2. ImageAttachment (M2 소유, M3이 소비)

`server/llm/types.py`:

```python
@dataclass(frozen=True)
class ImageAttachment:
    mime_type: str      # 계약 §1의 허용 MIME 중 하나
    content_base64: str # 검증된 base64 (검증 책임은 M1의 업로드 경로)

@dataclass(frozen=True)
class UserMessage:
    text: str
    images: tuple[ImageAttachment, ...] = ()  # 기본값 — 기존 호출부 무변경
```

- anthropic: images가 있으면 `content`를 블록 배열로 —
  `[{"type":"image","source":{"type":"base64","media_type":mime,"data":b64}}, ..., {"type":"text","text":text}]`
- gemini: `gtypes.Part.from_bytes(data=<decoded>, mime_type=mime)` + text Part
- claude_code: images 비어있지 않으면 모델 호출 없이
  `ModelTurn(text="현재 프로바이더(claude_code)는 이미지를 읽을 수 없습니다. provider.toml에서 anthropic 또는 gemini로 전환하세요.", ...)` 반환

## 3. 구조 사양 JSON (M3 소유, M4·UI가 소비)

툴 이름: `analyse_layout_image` (파라미터: `description: string` 필수 —
이미지 자체는 세션 보관분을 사용, base64 파라미터 없음)

```json
{"pattern": "rings | rows | grid | arc | scatter | single_point",
 "layers": [{"count": 6, "note": "inner"}, {"count": 12, "note": "outer"}],
 "symmetry": "radial | bilateral | none",
 "confidence": "high | medium | low",
 "annotations": [
   {"text": "간격 2m", "interpreted": {"spacing": 2.0}, "applies_to": "outer ring"},
   {"text": "MMX x6", "interpreted": {"type_name": "MMX", "count": 6}, "applies_to": "inner ring"}
 ],
 "unresolved": ["안쪽 링 반지름"]}
```

- `interpreted` 허용 키: `spacing`, `radius`, `z`, `count`, `type_name` (전부 optional)
- 픽셀 비율에서 추정한 수치는 어떤 필드에도 넣지 않는다 — 비전 프롬프트에 명시
- 이미지 없이 호출되면 error result: "첨부된 이미지가 없습니다"
- 콘솔로 0 exec verbs — `precheck_vectorworks_diff`와 같은 읽기 전용 부류

## 4. 파일 소유권 (충돌 방지)

| 슬라이스 | 수정 파일 | 신규 테스트 |
|---|---|---|
| M1 | server/web/messages.py, ui/src/protocol.ts, ui/src/App.tsx, ui/src/styles.css | server/tests/test_web_layout_image.py, ui/src/protocol.test.ts(추가), ui 컴포넌트 테스트 |
| M2 | server/llm/types.py, server/llm/anthropic_adapter.py, server/llm/gemini_adapter.py, server/llm/claude_code_adapter.py | server/tests/test_llm_image_attachments.py |
| M3 | server/orchestrator/tools.py (신규 툴+등록만, 기존 툴 무변경) | server/tests/test_layout_image_tool.py |

- M1은 `server/web/session.py`의 업로드 수신·보관 부분만 추가 가능 (새 메서드/필드,
  기존 흐름 무변경). M4(2차 웨이브)가 세션 배선을 잇는다.
- M3은 M2의 타입을 import하되 M2 파일을 수정하지 않는다. 타입이 아직 없으면
  계약 §2 형태를 전제로 작성 (2차 웨이브 전 통합 검증).
- 어느 슬라이스도 프로젝트 전체 테스트/린트/빌드를 돌리지 않는다 — 자기 신규
  테스트 파일만 실행. 전체 검증은 코디네이터가 마지막에 1회.
