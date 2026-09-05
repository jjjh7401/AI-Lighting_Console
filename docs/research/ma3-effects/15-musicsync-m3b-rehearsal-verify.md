# 타임코드 되읽기 검증 — Timecode 999

verdict: unverified
query_count: 3 (상한 4)

## 주장

타임코드 오브젝트가 존재하고 시퀀스가 매달려 있다는 것까지 관측했다. 여기까지가 이 채널이 말할 수 있는 전부다.

## 증거

- `pool_presence` [일치] — DataPool/Timecodes childCount 2, baseline 1 -> 2; slot 999 present as 'MSYNCPROBE'
- `name_match` [일치] — node name 'MSYNCPROBE' (expected 'MSYNCPROBE')
- `trackgroup` [일치] — DataPool/Timecodes/999/TrackGroup 1 childCount 2; children: MarkerTrack 'Marker', Track '<T215 SCRATCH DELETABLE>' (expected a Track named '<T215 SCRATCH DELETABLE>')

사유: three axes read; the event-content axis is outside the verified scope

운영자 인계분(앱 미발화): `Record Timecode 999`

## 기준 귀속

실기 콘솔 127.0.0.1:8000 · 회신 9005 · 2026-09-05T13:25:12+00:00 · 슬롯 999 · 조회 3/4

## 미검증

- 이 산출물의 판정은 `unverified` 이며 `verified` 가 아니다.
- `SongCueTimingSkip` [timecode_event_content] — M3-a 2회차는 TrackGroup 1 아래 트랙 목록까지만 열었다 — 트랙 아래 이벤트 내용은 이 채널로 관측되지 않았으므로(설계서 §5 갈래 B) 이 축은 검증 범위 밖이며, 좁혀진 사실로 보고한다

## 잔여 위험

- 이벤트 내용은 갈래 B 라 읽지 않았다 — 녹화된 이벤트가 계획과 일치한다는 주장은 하지 않는다
- 빈 타임코드 풀에서는 앱이 첫 타임코드를 못 만든다(t270) — 이 회차는 풀이 비어 있지 않았다
