"""SPEC-LDBEAT-001 M7 — 칸 데이터 구조화 + SCENE 메모 + 리그 일반화 (카드 t537).

콘솔 접촉 0건. 이 시험이 재는 것 다섯 가지:

1. LOVE ATTACK 30개 큐가 구조화 필드(브라이트니스/위치/색/효과 프리셋·
   `entry`·`source_ref`)로 옮겨졌는지 — §4가 준 네 자리만 전사되고
   나머지는 전부 미정(`None`)인지(REQ-LDBEAT-006(i-1)~(i-7)).
2. 레거시 `{bar,label}` 전용 칸을 읽을 때 구조화 필드가 전부 `None`이고
   `label`은 그대로 보여지는지 — 파싱·추측 0건(REQ-LDBEAT-006(ii)).
3. SCENE 열 값이 역할·효과 혼성 트랙으로 지어내지 않고 `scene_memos`로
   떨어지는지(리드 추가 지시, 2026-10-10) — 여섯 값 전부(BACK 충돌·
   WASH/FOH 그룹 번호 미확인·나머지 셀 그룹명 미지칭).
4. 겹침 거절(REQ-LDBEAT-004(h))이 칸 레벨 구조화와 독립인지(iii).
5. 로더가 리그·곡에 무관한 일반 코드인지 — LOVE ATTACK과 전혀 다른
   그룹 번호·이름의 가짜 데이터로도 같은 로더가 그 데이터를 그대로
   돌려주는지(카드 t537 추가 지시 2, "리그·디자인이 바뀌어도 동작").
"""

from __future__ import annotations

from server.design import beat_grid as beat_grid_module
from server.design.beat_grid import (
    LOVE_ATTACK_TITLE,
    attach_beat_grid_runtime_extras,
    classify_scene_cell_assignment,
    default_beat_grid,
    find_overlapping_group_tracks,
    normalize_beat_grid_cue,
    validate_beat_grid_tracks,
)
from server.design.beat_grid_probes import UNCONFIRMED_STATUS


class TestStructuredCueFields:
    def test_the_four_transcribed_cells_carry_value_percent_and_source_ref(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        by_name = {t["group_name"]: {c["bar"]: c for c in t["cues"]} for t in grid["tracks"]}

        back7 = by_name["BACK"][7]
        assert back7["brightness"]["mode"] == "value"
        assert back7["brightness"]["value_percent"] == 60
        assert back7["brightness"]["preset_no"] is None
        assert back7["source_ref"] == "reports/effect-arrangement-rules-20261007.md:106"

        back18 = by_name["BACK"][18]
        assert back18["brightness"]["value_percent"] == 100
        assert back18["source_ref"] == "reports/effect-arrangement-rules-20261007.md:109"

        back22 = by_name["BACK"][22]
        assert back22["brightness"]["value_percent"] == 100
        assert back22["source_ref"] == "reports/effect-arrangement-rules-20261007.md:110"

        blind18 = by_name["BLIND"][18]
        assert blind18["brightness"]["value_percent"] == 100
        assert blind18["source_ref"] == "reports/effect-arrangement-rules-20261007.md:109"

    def test_every_other_cue_has_no_value_percent_and_no_source_ref(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        known = {("BACK", 7), ("BACK", 18), ("BACK", 22), ("BLIND", 18)}
        # 카드 t543 — FOH bar 7 「FOH 켬」은 §4 출처 행은 있지만 밝기 숫자가 없다.
        foh_on = ("FOH", 7)

        checked = 0
        for track in grid["tracks"]:
            for cue in track["cues"]:
                checked += 1
                if (track["group_name"], cue["bar"]) in known:
                    continue
                assert cue["brightness"]["value_percent"] is None
                if (track["group_name"], cue["bar"]) == foh_on:
                    assert cue["source_ref"] == "reports/effect-arrangement-rules-20261007.md:106"
                    continue
                assert cue["source_ref"] is None
        assert checked == 31  # FOH 1 + WASH-ALL 0 + 7+7+7+7+2+0

    def test_no_cue_anywhere_invents_a_preset_number(self) -> None:
        # REQ-LDBEAT-015(f) — §4에 프리셋 번호가 0개이므로 30개 큐 전부
        # 네 프리셋 번호 필드가 None이다.
        grid = default_beat_grid(LOVE_ATTACK_TITLE)

        for track in grid["tracks"]:
            for cue in track["cues"]:
                assert cue["brightness"]["preset_no"] is None
                assert cue["position_preset_no"] is None
                assert cue["color_preset_no"] is None
                assert cue["effect_preset_no"] is None

    def test_entry_fade_bars_is_none_for_all_thirty_cues(self) -> None:
        # §4의 마디 단위 페이드 힌트는 전부 SCENE 열에만 있고 SCENE은
        # 트랙이 아니다(대응 큐 없음) — entry.fade_bars는 전수 None.
        grid = default_beat_grid(LOVE_ATTACK_TITLE)

        for track in grid["tracks"]:
            for cue in track["cues"]:
                assert cue["entry"]["fade_bars"] is None
                assert cue["entry"]["mib_mode"] is None

    def test_label_is_preserved_verbatim_for_display(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        by_name = {
            t["group_name"]: {c["bar"]: c["label"] for c in t["cues"]} for t in grid["tracks"]
        }

        assert by_name["BACK"][0] == "앞박 1회"
        assert by_name["BACK"][7] == "킥 1·2·4박 60%"


class TestLegacyCueReadPath:
    """REQ-LDBEAT-006(ii) — 구조화 필드가 하나도 없는 레거시 칸을 읽을 때."""

    def test_a_bare_bar_label_dict_normalizes_with_all_structured_fields_none(self) -> None:
        legacy = {"bar": 5, "label": "60% 느낌"}

        cue = normalize_beat_grid_cue(legacy)

        assert cue["bar"] == 5
        assert cue["label"] == "60% 느낌"  # 원문 그대로 — 숫자 "60"을 파싱하지 않는다
        assert cue["brightness"] == {"mode": None, "value_percent": None, "preset_no": None}
        assert cue["position_preset_no"] is None
        assert cue["color_preset_no"] is None
        assert cue["effect_preset_no"] is None
        assert cue["effect_kind"] is None
        assert cue["entry"] == {"fade_bars": None, "mib_mode": None}
        assert cue["source_ref"] is None

    def test_no_label_parsing_function_exists_in_the_legacy_read_path(self) -> None:
        # AC-LDBEAT-016(g) — 레거시-읽기 경로 소스에 label 파싱용 정규식·
        # 문자열 분해 함수가 0건(AC-LDBEAT-005 패턴과 동일한 grep 점검).
        import inspect

        source = inspect.getsource(normalize_beat_grid_cue)
        assert "label.split" not in source
        assert "re.match" not in source
        assert "re.search" not in source
        assert "re.findall" not in source

    def test_a_fully_structured_cue_passes_through_unchanged(self) -> None:
        structured = {
            "bar": 7,
            "label": "킥 1·2·4박 60%",
            "brightness": {"mode": "value", "value_percent": 60, "preset_no": None},
            "position_preset_no": None,
            "color_preset_no": None,
            "effect_preset_no": None,
            "effect_kind": None,
            "entry": {"fade_bars": None, "mib_mode": None},
            "source_ref": "reports/effect-arrangement-rules-20261007.md:106",
        }

        cue = normalize_beat_grid_cue(structured)

        assert cue == structured


class TestSceneMemos:
    """리드 추가 지시(2026-10-10) — SCENE 열 값은 역할·효과 혼성 트랙으로
    지어내지 않고 메모로 떨어진다. 겹침 검증 로직과는 독립이다."""

    def test_all_six_scene_values_become_memos(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)

        assert len(grid["scene_memos"]) == 6
        bars = sorted(memo["bar"] for memo in grid["scene_memos"])
        assert bars == [0, 7, 11, 14, 18, 22]

    def test_each_memo_carries_the_verbatim_section_4_text_and_source_line(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        by_bar = {memo["bar"]: memo for memo in grid["scene_memos"]}

        assert "BACK 차가운 실루엣 30%" in by_bar[0]["text"]
        assert by_bar[0]["source_ref"] == "reports/effect-arrangement-rules-20261007.md:104"
        assert "워시 25% 덜어냄" in by_bar[14]["text"]
        assert by_bar[14]["source_ref"] == "reports/effect-arrangement-rules-20261007.md:108"

    def test_scene_memos_are_a_separate_list_outside_track_cues(self) -> None:
        # 메모는 트랙 큐에 끼워넣지 않는다 — BACK 트랙은 여전히 7개 큐뿐이다
        # (충돌한 bar=0 메모가 BACK 큐를 밀어내거나 덮어쓰지 않는다).
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        back = next(t for t in grid["tracks"] if t["group_name"] == "BACK")

        assert len(back["cues"]) == 7
        assert back["cues"][0]["label"] == "앞박 1회"  # 메모가 덮어쓰지 않았다

    def test_other_songs_have_no_scene_memos(self) -> None:
        grid = default_beat_grid("Sugar")

        assert grid["scene_memos"] == []


class TestSceneCellAssignmentRule:
    """REQ-LDBEAT-006(iv-2) "세 조건" 규칙의 파라미터화 시험(plan-audit
    iteration 3 D4). 리그·곡 전용 그룹 이름은 이 클래스의 테스트 데이터에만
    있다 — `beat_grid.py`의 `classify_scene_cell_assignment` 자체는 어떤
    리그·곡 이름도 모른다(카드 t537 추가 지시 2, 로더 일반화와 같은 원칙)."""

    def test_condition_1_fails_when_the_cell_does_not_name_a_group(self) -> None:
        verdict = classify_scene_cell_assignment(
            named_group=None,
            confirmed_track_group_names=["BACK"],
            group_has_existing_cue_at_bar=False,
        )
        assert verdict == "memo"

    def test_condition_2_fails_when_the_named_group_has_no_confirmed_track(self) -> None:
        verdict = classify_scene_cell_assignment(
            named_group="WASH",
            confirmed_track_group_names=["BACK", "SIDE-ALL"],
            group_has_existing_cue_at_bar=False,
        )
        assert verdict == "memo"

    def test_condition_3_fails_when_the_group_already_has_a_cue_at_that_bar(self) -> None:
        verdict = classify_scene_cell_assignment(
            named_group="BACK",
            confirmed_track_group_names=["BACK"],
            group_has_existing_cue_at_bar=True,
        )
        assert verdict == "memo"

    def test_all_three_conditions_true_moves_the_value_to_a_track_cue(self) -> None:
        verdict = classify_scene_cell_assignment(
            named_group="BACK",
            confirmed_track_group_names=["BACK"],
            group_has_existing_cue_at_bar=False,
        )
        assert verdict == "track"

    def test_love_attack_section_4_scene_cells_all_classify_as_memo(self) -> None:
        # beat_grid_data/love_attack.yaml 주석(2026-10-10 전수 재검토)이
        # 수동으로 판단한 여섯 자리를 이 순수 함수로 재도출한다 — 아래
        # 입력(named_group/confirmed_track_group_names/
        # group_has_existing_cue_at_bar)은 §4 원문 + YAML 주석이 적은 근거를
        # 그대로 옮긴 **이 테스트 전용** 데이터이고, `beat_grid.py`의
        # 함수 로직에는 올라가지 않는다(리그 전용 상수를 app 로직에 더하지
        # 않는다).
        # 카드 t543 — FOH(3)·WASH-ALL(10) 이 콘솔 실측으로 확인된 트랙이 됐다.
        love_attack_confirmed_tracks = [
            "FOH",
            "WASH-ALL",
            "BACK",
            "SIDE-ALL",
            "MOVER-U",
            "MOVER-D",
            "BLIND",
        ]
        section_4_scene_inputs: dict[int, dict[str, object]] = {
            # bar 0 — BACK을 직접 부르고 그룹 번호도 확인돼 있지만, 그
            # 마디에 이미 펄스 큐("앞박 1회")가 있어 조건 3이 거짓.
            0: {
                "named_group": "BACK",
                "confirmed_track_group_names": love_attack_confirmed_tracks,
                "group_has_existing_cue_at_bar": True,
            },
            # bar 7 — 「워시」 부분: 칸이 부르는 이름은 "WASH" 이고 확인된
            # 트랙은 "WASH-ALL" 이다 — 바이트 일치가 아니라 조건 2가 거짓
            # (카드 t543, 워시 = WASH-ALL 로 읽을지는 리드 결정). 같은 칸의
            # 「FOH 켬」 부분은 아래에서 따로 "track" 으로 잰다.
            7: {
                "named_group": "WASH",
                "confirmed_track_group_names": love_attack_confirmed_tracks,
                "group_has_existing_cue_at_bar": False,
            },
            # bar 11/14/18/22 — 칸 자체가 그룹 이름을 부르지 않는다(조건 1이
            # 거짓).
            11: {
                "named_group": None,
                "confirmed_track_group_names": love_attack_confirmed_tracks,
                "group_has_existing_cue_at_bar": False,
            },
            14: {
                "named_group": None,
                "confirmed_track_group_names": love_attack_confirmed_tracks,
                "group_has_existing_cue_at_bar": False,
            },
            18: {
                "named_group": None,
                "confirmed_track_group_names": love_attack_confirmed_tracks,
                "group_has_existing_cue_at_bar": False,
            },
            22: {
                "named_group": None,
                "confirmed_track_group_names": love_attack_confirmed_tracks,
                "group_has_existing_cue_at_bar": False,
            },
        }

        derived_verdicts = {
            bar: classify_scene_cell_assignment(**inputs)  # type: ignore[arg-type]
            for bar, inputs in section_4_scene_inputs.items()
        }
        assert all(verdict == "memo" for verdict in derived_verdicts.values())

        # 카드 t543 — bar 7 칸의 「FOH 켬」은 FOH 를 바이트로 부르고, FOH(3)가
        # 확인된 트랙이며, 그 자리에 기존 큐가 없다 → "track". YAML 의 FOH
        # 트랙이 바로 그 큐 하나를 싣는다.
        assert (
            classify_scene_cell_assignment(
                named_group="FOH",
                confirmed_track_group_names=love_attack_confirmed_tracks,
                group_has_existing_cue_at_bar=False,
            )
            == "track"
        )
        foh = next(
            t for t in default_beat_grid(LOVE_ATTACK_TITLE)["tracks"] if t["group_name"] == "FOH"
        )
        assert [(c["bar"], c["label"]) for c in foh["cues"]] == [(7, "FOH 켬")]

        # 이 순수 함수가 도출한 "전부 memo"가, YAML이 실제로 싣고 있는
        # scene_memos의 bar 집합과 바이트 단위로 일치하는지 확인한다.
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        yaml_memo_bars = sorted(memo["bar"] for memo in grid["scene_memos"])
        assert yaml_memo_bars == sorted(section_4_scene_inputs.keys())


class TestOverlapIndependentOfCellStructuring:
    """REQ-LDBEAT-006(iii) — 겹침 거절은 칸 레벨 구조화 변경과 독립이다."""

    def test_love_attack_default_still_passes_validation(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)

        assert validate_beat_grid_tracks(grid["tracks"]) is None

    def test_overlap_rejection_reads_group_name_only_not_cue_content(self) -> None:
        tracks_legacy_cells = [
            {"group_name": "MOVER-ALL", "cues": [{"bar": 0, "label": "—"}]},
            {"group_name": "MOVER-U", "cues": [normalize_beat_grid_cue({"bar": 0, "label": "x"})]},
        ]
        tracks_structured_cells = [
            {
                "group_name": "MOVER-ALL",
                "cues": [
                    normalize_beat_grid_cue({"bar": 0, "label": "y", "color_preset_no": "4.21"})
                ],
            },
            {
                "group_name": "MOVER-U",
                "cues": [
                    normalize_beat_grid_cue({"bar": 0, "label": "z", "effect_kind": "position"})
                ],
            },
        ]

        reason_legacy = validate_beat_grid_tracks(tracks_legacy_cells)
        reason_structured = validate_beat_grid_tracks(tracks_structured_cells)

        assert reason_legacy is not None
        assert reason_structured is not None
        assert reason_legacy == reason_structured  # 바이트 동일 — 칸 내용 무관

    def test_overlap_functions_have_no_scene_memos_parameter_or_reference(self) -> None:
        # AC-LDBEAT-016(l)/plan-audit iteration 3 D2 — find_overlapping_group_
        # tracks·validate_beat_grid_tracks 둘 다 scene_memos를 매개변수로 받지
        # 않고(함수 시그니처가 구조적으로 배제), 소스 자체에도 scene_memos
        # 참조가 0건이다(REQ-LDBEAT-006(iv-4)).
        import inspect

        overlap_signature = inspect.signature(find_overlapping_group_tracks)
        validate_signature = inspect.signature(validate_beat_grid_tracks)
        assert "scene_memos" not in overlap_signature.parameters
        assert "scene_memos" not in validate_signature.parameters

        overlap_source = inspect.getsource(find_overlapping_group_tracks)
        validate_source = inspect.getsource(validate_beat_grid_tracks)
        assert "scene_memos" not in overlap_source
        assert "scene_memos" not in validate_source

    def test_scene_memo_bars_that_coincide_with_existing_cues_do_not_affect_validation(
        self,
    ) -> None:
        # 행동 시험(AC-LDBEAT-016(l)) — scene_memos가 큐처럼 취급됐다면 같은
        # 마디에 이미 있는 트랙 큐와 "충돌"할 법도 한데, scene_memos는 이
        # 함수에 아예 전달되지 않으므로(위 시험이 확인한 시그니처 배제)
        # 겹침 판정 결과가 전혀 바뀌지 않는다 — LOVE ATTACK 기본값으로
        # 겹치는 마디가 실제로 있는지부터 양성 대조한다.
        grid = default_beat_grid(LOVE_ATTACK_TITLE)
        memo_bars = {memo["bar"] for memo in grid["scene_memos"]}
        cue_bars_colliding_with_memos = {
            cue["bar"]
            for track in grid["tracks"]
            for cue in track["cues"]
            if cue["bar"] in memo_bars
        }
        # 양성 대조 — 메모 자리와 큐 자리가 실제로 겹치지 않으면 이 시험은
        # scene_memos 독립성에 대해 아무것도 증명하지 못한다.
        assert cue_bars_colliding_with_memos, "전제 깨짐: 메모·큐가 공유하는 마디가 없다"

        assert validate_beat_grid_tracks(grid["tracks"]) is None


class TestProbeResultsEmbedding:
    def test_default_beat_grid_carries_an_unconfirmed_stub(self) -> None:
        grid = default_beat_grid(LOVE_ATTACK_TITLE)

        assert grid["probe_results"] == {i: UNCONFIRMED_STATUS for i in range(1, 10)}

    def test_runtime_extras_refreshes_probe_results_from_a_real_progress_md(self, tmp_path) -> None:
        progress = tmp_path / "progress.md"
        progress.write_text(
            "| 항목 | 판정 | 무엇을 봤나 | 근거 |\n"
            "|---|---|---|---|\n"
            "| ① 타임코드 트랙 ≥3(목표 6) | **통과(구조)** | x | y |\n",
            encoding="utf-8",
        )
        payload = {"beat_grid": default_beat_grid(LOVE_ATTACK_TITLE)}

        refreshed = attach_beat_grid_runtime_extras(payload, progress_md_path=progress)

        assert refreshed["beat_grid"]["probe_results"][1] == "통과(구조)"
        assert refreshed["beat_grid"]["probe_results"][2] == UNCONFIRMED_STATUS

    def test_runtime_extras_is_a_no_op_when_beat_grid_is_absent(self) -> None:
        payload = {"song_title": "Sugar"}

        refreshed = attach_beat_grid_runtime_extras(payload, progress_md_path=None)

        assert refreshed == payload

    def test_runtime_extras_normalizes_any_legacy_cues_for_display(self, tmp_path) -> None:
        grid = {
            "song_title": "Sugar",
            "bar_range": {"start": 0, "end": 25},
            "tracks": [
                {
                    "group_no": 1,
                    "group_no_confirmed": True,
                    "group_name": "CUSTOM",
                    "layer_role": None,
                    "cues": [{"bar": 0, "label": "레거시"}],
                }
            ],
            "scene_memos": [],
            "probe_results": {},
            "source": "custom",
            "note": None,
        }
        payload = {"beat_grid": grid}

        refreshed = attach_beat_grid_runtime_extras(
            payload, progress_md_path=tmp_path / "absent.md"
        )

        cue = refreshed["beat_grid"]["tracks"][0]["cues"][0]
        assert cue["label"] == "레거시"
        assert cue["brightness"] == {"mode": None, "value_percent": None, "preset_no": None}


class TestLoaderIsRigAndSongAgnostic:
    """카드 t537 추가 지시 2 — "리그·디자인이 바뀌어도 동작해야 한다".
    로더(``default_beat_grid``)에 LOVE ATTACK 전용 그룹 번호·이름이
    하드코딩돼 있다면, 레지스트리에 끼워 넣은 **다른** 가짜 곡 데이터
    (전혀 다른 그룹 번호·이름)가 그대로 나오지 않을 것이다."""

    def test_a_different_songs_registered_data_comes_back_unchanged_by_any_love_attack_logic(
        self, monkeypatch, tmp_path
    ) -> None:
        fake_song = "A Totally Different Rig Song"
        fake_doc = {
            "source": "fake_song_default",
            "tracks": [
                {
                    "group_name": "WEIRD-GROUP-99",
                    "group_no": 999,
                    "group_no_confirmed": True,
                    "cues": [{"bar": 0, "label": "뭔가 다른 동작"}],
                }
            ],
            "scene_memos": [{"bar": 0, "text": "다른 곡 메모", "source_ref": "nowhere:1"}],
        }
        fake_path = tmp_path / "fake_song.yaml"
        import yaml

        fake_path.write_text(yaml.safe_dump(fake_doc, allow_unicode=True), encoding="utf-8")

        key = beat_grid_module._group_key(fake_song)
        monkeypatch.setitem(beat_grid_module._SONG_DEFAULT_FILES, key, fake_path)

        grid = default_beat_grid(fake_song)

        assert grid["source"] == "fake_song_default"
        assert grid["tracks"][0]["group_name"] == "WEIRD-GROUP-99"
        assert grid["tracks"][0]["group_no"] == 999
        assert grid["scene_memos"][0]["text"] == "다른 곡 메모"
        # LOVE ATTACK 전용 이름·번호가 전혀 섞여 들지 않았다.
        names = [t["group_name"] for t in grid["tracks"]]
        assert "BACK" not in names
        assert "MOVER-U" not in names

    def test_find_overlapping_group_tracks_has_no_song_specific_branch(self) -> None:
        # 이 함수는 접두 규칙 하나만으로 LOVE ATTACK 밖의 그룹 이름에도 똑같이
        # 동작한다 — 로직에 "BACK"·"MOVER" 같은 리터럴이 전혀 없다.
        import inspect

        source = inspect.getsource(find_overlapping_group_tracks)
        for rig_specific_literal in ("BACK", "MOVER-U", "MOVER-D", "SIDE-ALL", "BLIND", "STROBE"):
            assert rig_specific_literal not in source

        conflict = find_overlapping_group_tracks(["RIG99-ALL", "RIG99-L"])
        assert conflict == ("RIG99-ALL", "RIG99-L")


class TestLiveProbeReadThroughTheRealSessionWiring:
    """REQ-LDBEAT-003(b)/AC-LDBEAT-009(c) — M1 상태 화면은 손으로 옮긴 TS
    상수가 아니라 progress.md를 그 자리에서 읽는 살아있는 소스다. 이
    시험은 가짜 경로가 아니라 **실제 저장소의 progress.md**를 읽어
    `server/web/session.py`의 실제 서빙 경로(`_song_timeline_payload`)가
    그 값을 내보내는지 확인한다(서버 쪽 wiring이 실제로 호출되는지,
    `test_beat_grid_t532.py`의 `TestSongTimelinePayloadWiring`과 같은 성격)."""

    def test_the_real_session_payload_carries_the_live_progress_md_table(self) -> None:
        from server.design.beat_grid_probes import default_progress_md_path
        from server.design.energy import EFFECT_AXIS_CAPABILITY
        from server.design.profile import MusicProfile
        from server.design.rig import build_rig_profile
        from server.design.song_cue_composer import compose_song_cue_bundle
        from server.design.song_plan import (
            AccentDecision,
            ApprovalState,
            DLevelDecision,
            FxDecision,
            PaletteDecision,
            PositionDecision,
            SectionDecision,
            TextureDecision,
            TimestampedSection,
            TimingPlan,
            UnifiedSongLightingPlan,
        )
        from server.web.session import _song_timeline_payload

        # 이 시험이 실제 파일을 읽는다는 것 자체를 먼저 확인한다 — 파일이
        # 없는 환경(예: 번들)에서는 이 전제가 깨지므로 그 경우는 스스로
        # 건너뛴다(거짓 FAIL을 만들지 않는다).
        real_path = default_progress_md_path()
        if not real_path.exists():
            import pytest

            pytest.skip("이 환경에는 .moai/specs/SPEC-LDBEAT-001/progress.md가 없음")

        rig = build_rig_profile(
            patch=[
                {"fid": fid, "type_name": "Fixture", "capabilities": [EFFECT_AXIS_CAPABILITY]}
                for fid in range(1, 5)
            ],
            groups={},
            coords=[],
            declared_layers={"back": [1, 2]},
        )
        section = SectionDecision(
            section=TimestampedSection(
                index=1, label="INTRO", start_ms=0, source="song_design_interview"
            ),
            d=DLevelDecision(level=2, source="section_mood"),
            palette=PaletteDecision(colors=("hot_pink",), source="director"),
            position=PositionDecision(preset="Center", source="director"),
            texture=TextureDecision(label="long fade", source="genre"),
            fx=FxDecision(allowed=(), density=0),
            accent=AccentDecision(),
            cue_number=10,
        )
        plan = UnifiedSongLightingPlan(
            song_title=LOVE_ATTACK_TITLE,
            sequence_name="LOVE ATTACK Seq",
            sections=(section,),
            timing=TimingPlan.timecode(77),
            music_profile=MusicProfile(bpm=120.0, meter="4/4", key_mode="D♭ major"),
            rig_profile=rig,
            approval=ApprovalState.approved(reviewer="LD"),
        )

        payload = _song_timeline_payload(
            plan, compose_song_cue_bundle(plan), lifecycle="pending_approval", sequence_no=1
        )

        live = payload["beat_grid"]["probe_results"]
        from_disk = read_m1_probe_results_from_path_for_test(real_path)
        assert live == from_disk
        assert set(live.keys()) == set(range(1, 10))


def read_m1_probe_results_from_path_for_test(
    path,
):  # pragma: no cover - thin re-export for the test above
    from server.design.beat_grid_probes import read_m1_probe_results_from_path

    return read_m1_probe_results_from_path(path)
