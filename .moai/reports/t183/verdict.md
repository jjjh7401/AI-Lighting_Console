# t183 판정 - 여섯 자리 도달 측정, 도달하는 것만 고친다

> 2026-08-31. 기준 origin/main e25930c. 트리 .claude/worktrees/t183 (WT-inventory-error-reach).
> 리드 재측정 좌표를 내가 독립으로 재확인했다. 착수 시점 재측정.

---

## 0. 결론 먼저

여섯 자리 전부 도달한다. 예외 없음.

| 좌표 | 함수 | 도달 |
|---|---|---|
| tools.py:2912 | precheck_patch | 도달한다 |
| tools.py:3095 | precheck_vectorworks_diff | 도달한다 |
| tools.py:3277 | apply_vectorworks_patch | 도달한다 |
| tools.py:3910 | resolve_patch_address | 도달한다 |
| tools.py:4486 | patch_fixtures._verify | 도달한다 (호출부 4513 · 4584 둘 다 실행 경로) |
| tools.py:6525 | build_patch_sheet (다른 함수를 감싼다) | 도달한다 - 그 다른 함수도 결국 read_inventory 로 바닥난다 |

조이는 방향이라 적용 여부는 리드에게 넘긴다. 코드는 안 고쳤다 - 패치안만 3절에 제안한다.

---

## 1. 좌표 독립 재확인

배차서 값을 옮기지 않고 내가 직접 쟀다.

    grep -n "except InventoryReadError" server/orchestrator/tools.py
    -> 2912 · 3095 · 3277 · 3910 · 4304 · 4486 · 5442 · 6525  (8자리, 리드 재측정과 완전 일치)

    grep -n "raise StateQueryError" server/safety/console.py
    -> 689 · 693 · 713 · 718 · 748 · 752 · 772 · 777  (8자리)
    grep -c "raise StateQueryError" server/safety/console.py -> 8

카드 본문의 "다섯"은 리드가 이미 정정했고(head -5 로 개수를 잘못 읽음, lane-protocol
4.0절이 이번에 이름 붙인 함정과 같은 형태), 내 독립 측정도 8을 낸다. head 없이
grep -n 과 grep -c 로 쟀다.

4304(patch_fixtures)와 5442(import_lxseq_patch)는 t181 이 이미 고쳤다 -
except StateQueryError 형제가 각각 바로 앞에 붙어 있다(:4295 · :5433 확인).
그러므로 이 카드의 대상은 남은 여섯이다.

---

## 2. 도달 측정 - 술어와 근거

### 2.1 read_inventory 가 어디서 StateQueryError 를 흘리는지부터

server/prechk/inventory.py:

    _root_payload (:402-416)  -- FIXTURE_ROOT 쿼리, read_inventory 가 매번 먼저 부른다
      payload = port.query_state(FIXTURE_ROOT)   <- try/except 없음. 감싸지 않는다
      if not payload.get("ok"): raise InventoryReadError(...)   <- 이건 정상 반환 뒤의 값 검사

    _probe_slot (:440-450)  -- 슬롯별 보강 쿼리
      try:
          payload = port.query_state(path)
      except Exception as error:   <- 여기는 감싼다. StateQueryError 도 흡수돼 ReadFailure 로 변한다

핵심: root 쿼리와 슬롯 쿼리는 예외 처리가 다르다. read_inventory 는 슬롯 순회 전에
반드시 root 쿼리를 먼저 하므로(모든 호출이 이 경로를 탄다), 콘솔이 타임아웃하거나
ok:false 로 답하면 server/safety/console.py:689·693 이 StateQueryError 를 던지고
그게 _root_payload 를 감싸는 게 없어 read_inventory 밖으로 그대로 나간다. 이게
"팔 A" 다 - 카드가 이미 t181 단위 측정으로 증명한 것과 정합적이다.

### 2.2 여섯 자리 각각 - try 블록에 무엇이 더 있는가

여섯 자리 전부 같은 모양이다:

    try:
        inventory = read_inventory(_InventoryPort(state_port, property_port))
    except InventoryReadError as error:
        return _error_result(call, f"fixture inventory unreadable: {error}")

try 안에 read_inventory 호출 하나뿐이고, except 도 InventoryReadError 하나뿐이다.
StateQueryError 를 미리 가로채는 다른 except 도, 다른 포트로 바꿔치기하는 분기도
없다. _InventoryPort.query_state(:2769-2770)는 self._state.query_state(path) 를
그대로 위임하고, state_port 는 build_toolset 클로저가 여섯 자리 전부에 같은
객체를 준다 - 별도의 안전 포트가 없다.

### 2.3 6525(build_patch_sheet) - "다른 함수"도 결국 같은 바닥

카드가 "형제 레인의 단위 측정이 적용 안 된다"고 표시한 자리다. 확인했다:

    tools.py 의 build_patch_sheet (툴)
      -> server.paperwork.data.build_patch_sheet (별칭 build_patch_sheet_query)
         -> :100  inventory = read_inventory(port, policy)   <- 여기도 감싸지 않는다

paperwork/data.py 의 build_patch_sheet 함수 안에서 read_inventory 호출에
try/except 가 없다. 즉 "다른 함수"라는 것은 사실이지만 그 함수도 결국
read_inventory 를 직접 부르고 안 감싸므로, 단위 측정의 결론(StateQueryError 가
그대로 샌다)이 그대로 적용된다 - 다만 이건 추정이 아니라 이번에 직접 읽어서
확인한 것이다.

### 2.4 4486(_verify) - 호출부까지 확인

_verify() 는 patch_fixtures 안의 클로저다. 호출부 둘 다 확인했다:

    :4513  after, read_error = _verify()   <- _fire() 직후, 조건 없이 실행
    :4584  after, read_error = _verify()   <- 사람 재시도 분기 안, 그래도 실행 경로

첫 호출은 패치 쓰기가 실제로 발화될 때마다 도는 주 경로다 - 조건문 뒤가 아니다.
그러므로 4486 은 이론상 존재가 아니라 실행 시 실제로 도는 코드다.

---

## 3. 제안 패치 - 적용은 리드 판단

StateQueryError 는 이미 tools.py:130 에서 import 돼 있다(t181 이 4295·5433 에서 이미
쓰고 있다). 같은 패턴을 여섯 자리에 반복하면 된다 - t181 이 4295 에 남긴 형태:

    try:
        inventory = read_inventory(_InventoryPort(state_port, property_port))
    except StateQueryError as error:
        return _error_result(
            call, f"console did not answer - fixture inventory unread: {error}"
        )
    except InventoryReadError as error:
        return _error_result(call, f"fixture inventory unreadable: {error}")

이건 코드를 안 고치고 예외 흐름만 넓힌다 - 지금 서버 내부 오류처럼 보이던 것이
"콘솔이 안 답했다"는 정확한 사유로 바뀐다. 조이는 방향이다 - 지금 (아마도
프로토콜 예외로) 죽던 도구 호출이 구조화된 거절 응답으로 바뀐다. 그래서 적용은
안 했다 - lane-protocol 7절 "조이는 변경은 리드가 판정한다"를 따른다.

6525(build_patch_sheet)는 read_inventory 를 직접 안 부르므로 이 패턴을 그대로
못 붙인다 - paperwork/data.py 의 build_patch_sheet 함수를 감싸는 형태가 되어야
한다. 두 갈래 중 하나: (a) paperwork/data.py 안에서 StateQueryError 를 잡아
다시 던지거나, (b) tools.py 호출부에서 바깥쪽에 형제 except 를 추가한다. 어느
쪽이든 paperwork 모듈이 tools.py 의 StateQueryError 를 알아야 하므로 import
경계를 하나 더 넘는다 - 이것도 리드 판단이 필요하다.

---

## 4. 안 잰 것

- 여섯 자리를 실제로 고쳤을 때 test_lxseq_preset_safety.py 류의 기존 검사가
  깨지는지 - 코드를 안 고쳤으므로 안 돌렸다
- 콘솔 실기로 타임아웃/ok:false 를 실제로 유발해 이 경로를 라이브로 타봤는지 -
  이 카드는 판독 카드라 실기 0회, 실제로 안 했다
- paperwork/data.py 의 build_patch_sheet 를 부르는 다른 호출부가 더 있는지 -
  tools.py 안의 이 하나만 확인했다
- _verify 의 두 번째 호출부(:4584)로 가는 사람 재시도 분기가 실제로 얼마나
  자주 타는지 - 도달 자체는 확인했지만 빈도는 안 쟀다

---

## 5. 측정 조건

    origin/main   e25930c
    트리          .claude/worktrees/t183 (WT-inventory-error-reach)
    좌표          server/orchestrator/tools.py:2912·3095·3277·3910·4486·6525
                  server/prechk/inventory.py:402-450 (_root_payload·_probe_slot)
                  server/paperwork/data.py:81-100 (build_patch_sheet)
                  server/safety/console.py:669-694 (query_state)
    콘솔          불필요, 접촉 0
    코드 변경     0행
