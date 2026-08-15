# AI Lighting Console worktree and branch map

## Conclusion
Current directory `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console` is not `main`; it is the `jjjh7401/ui-user-guide` worktree. Do not implement spatial-height editing there.

## Active worktrees

| Path | Branch | HEAD | Purpose/status |
|---|---|---|---|
| `/Users/studiox/Documents/Claude/Code/AI-Lighting_Console` | `jjjh7401/ui-user-guide` | `23b3e6e` | Current UI/user-guide/cue-monitor branch; 19 commits beyond common base. |
| `/Users/studiox/orca/workspaces/AI-Lighting_Console/spec-vwx-001` | `main` | `63083a6` | Main integration worktree; includes spatial read/write history. |
| `/Users/studiox/orca/workspaces/AI-Lighting_Console/e2e-live` | `spec/introspect-001` | `c7780f5` | Separate introspection/E2E branch; unrelated to spatial-height implementation. |

## Branch relationship

- Common base of current branch and `main`: `3176900`.
- Current branch-only commits: 19.
- `main`-only commits: 156.
- Spatial read/write feature commit: `1c72d3e feat(spatial): SPEC-COPILOT-SPATIAL-001 run 완결 — 공간 배치 인식·생성(READ/WRITE)`.
- `1c72d3e` is reachable from `main`; it is not an ancestor of the current branch.

## Why the current Copilot rejects layout edits

The current checkout has 19 registered model tools and does not register `get_spatial_context` or `arrange_fixtures`. Its `server/spatial/` Python source is absent. The user guide still advertises `get_spatial_context`, so documentation and runtime capability are inconsistent.

The spatial feature in `main` provides:

- `get_spatial_context`: reads fixture FID and X/Y/Z coordinates.
- `arrange_fixtures`: writes Patch `Posx`, `Posy`, and `Posz` through the standard safety-gated command path; it creates coordinate backups, returns a restore bundle, and reads coordinates back to verify writes.

## Required implementation path

1. Preserve `jjjh7401/ui-user-guide` as a UI/documentation-only change set.
2. Rebase or merge that branch into current `main` separately before its own PR, if those changes are intended to ship.
3. Create a new dedicated worktree and branch from the latest `main`:
   - Branch: `feature/SPEC-COPILOT-SPATIAL-HEIGHT-001`
   - Worktree: `/Users/studiox/orca/workspaces/AI-Lighting_Console/spatial-height-001`
4. In that new branch, add a height-only coordinate mutation that sets `Posz` while preserving existing `Posx`, `Posy`, and orientation; retain backup, gate, verification, and restore behavior.
5. Merge the spatial-height PR into `main`, rebuild/deploy the app, restart the backend/application, and start a new Copilot conversation. Gemini caches the toolset with the system prompt, so a running process may retain the old tool list.

## Target command behavior

Input:

```text
레이아웃 전체 장비 바닥에서 5m로
```

Interpretation:

```text
For every patched lighting fixture: set Posz = 5.0 m.
Preserve Posx, Posy, orientation, DMX values, Pan/Tilt, cues, and presets.
```
