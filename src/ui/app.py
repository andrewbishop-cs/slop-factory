"""Streamlit review panel (M8).

A local browser dashboard to run and review the factory:
  • browse by **series → episode** (sidebar pickers);
  • **create a new series** (writes a validated bible — adding a series is config, not code);
  • **generate** a new episode (or continue the arc) by shelling out to the orchestrator;
  • per-episode: the script, an **image gallery with per-image re-roll**, the `final.mp4`
    player, the **QC report**, the auto-caption, and **approve / reject**.

Heavy generation (FLUX/LTX/etc.) runs in a subprocess via the orchestrator/images CLIs so the
UI process never imports torch and a model crash can't take the dashboard down. QC and the
upload stub are light, so they're called in-process.

Run: uv run streamlit run src/ui/app.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import streamlit as st

from src.config import (
    PROJECT_ROOT,
    SERIES_DIR,
    Settings,
    load_series_bible,
    load_settings,
    save_series_bible,
)
from src.pipeline import qc
from src.schemas import Character, Episode, PlotState, SeriesBible
from src.upload import tiktok_stub

# Mirror orchestrator.STAGES here so the UI never imports the orchestrator (which pulls in torch).
STAGES = ["script", "images", "tts", "captions", "music", "hook", "assemble", "qc"]


# --------------------------------------------------------------------------- filesystem helpers


def list_series() -> list[str]:
    return sorted(p.stem for p in SERIES_DIR.glob("*.json"))


def list_episodes(settings: Settings, series_id: str) -> list[str]:
    episodes_dir = settings.episodes_dir()
    if not episodes_dir.exists():
        return []
    return sorted(p.name for p in episodes_dir.glob(f"{series_id}_ep_*") if p.is_dir())


def load_episode(episode_dir: Path) -> Episode | None:
    f = episode_dir / "episode.json"
    if not f.exists():
        return None
    try:
        return Episode.model_validate_json(f.read_text())
    except Exception as e:  # a half-written / schema-drifted episode shouldn't crash the UI
        st.error(f"episode.json failed to validate: {e}")
        return None


def load_state(episode_dir: Path) -> dict[str, bool]:
    f = episode_dir / "state.json"
    return json.loads(f.read_text()) if f.exists() else {}


def load_review(episode_dir: Path) -> dict[str, Any]:
    f = episode_dir / "review.json"
    if f.exists():
        return json.loads(f.read_text())
    return {"approved": False, "rejected": False, "note": ""}


def save_review(episode_dir: Path, review: dict[str, Any]) -> None:
    (episode_dir / "review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")


def load_qc_report(episode_dir: Path) -> dict[str, Any] | None:
    f = episode_dir / "qc_report.json"
    return json.loads(f.read_text()) if f.exists() else None


def _episode_cliffhanger(episode_dir: Path) -> str | None:
    """Read an episode's cliffhanger straight from JSON (tolerant of stale/old-schema episodes)."""
    f = episode_dir / "episode.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text()).get("cliffhanger_text")
    except (json.JSONDecodeError, OSError):
        return None


def delete_episode(settings: Settings, series_id: str, episode_id: str) -> None:
    """Delete an episode's folder and roll the series bible's plot_state back to before it was made.

    `script_gen` only mutates `last_cliffhanger` + `episode_log` (never `active_threads`), so the
    rollback drops this episode's log entry and restores `last_cliffhanger` from the newest remaining
    episode — or, when an exact `plot_state_before.json` snapshot exists for the newest episode, from that.
    """
    episodes_dir = settings.episodes_dir()
    episode_dir = episodes_dir / episode_id
    remaining = [e for e in list_episodes(settings, series_id) if e != episode_id]
    is_newest = all(e < episode_id for e in remaining)  # ids are zero-padded → lexicographic == numeric

    try:
        bible = load_series_bible(series_id)
    except Exception:
        bible = None

    if bible is not None:
        snapshot = episode_dir / "plot_state_before.json"
        restored = False
        if is_newest and snapshot.exists():
            try:
                bible.plot_state = PlotState.model_validate_json(snapshot.read_text())
                restored = True
            except Exception:
                restored = False
        if not restored:
            bible.plot_state.episode_log = [
                e for e in bible.plot_state.episode_log if not e.startswith(f"{episode_id}:")
            ]
            if is_newest:
                newest = max(remaining) if remaining else None
                bible.plot_state.last_cliffhanger = _episode_cliffhanger(episodes_dir / newest) if newest else None
        save_series_bible(bible)

    shutil.rmtree(episode_dir, ignore_errors=True)


# --------------------------------------------------------------------------- subprocess runner


def run_module(args: list[str], label: str) -> bool:
    """Run `python -m <args>` from the repo root, capturing output into session_state.

    Returns True on exit 0. Used for the heavy stages so torch lives in a child process.
    """
    cmd = [sys.executable, "-m", *args]
    with st.spinner(f"{label} … (this can take several minutes for image/video stages)"):
        proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    st.session_state["last_run"] = {
        "label": label,
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "out": ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()[-12000:] or "(no output)",
    }
    return proc.returncode == 0


def render_last_run() -> None:
    lr = st.session_state.get("last_run")
    if not lr:
        return
    (st.success if lr["ok"] else st.error)(
        f"{lr['label']}: {'done' if lr['ok'] else f'FAILED (exit {lr['code']})'}"
    )
    with st.expander(f"output — {lr['label']}", expanded=not lr["ok"]):
        st.code(lr["out"])


# --------------------------------------------------------------------------- sidebar: new series


def new_series_form() -> None:
    with st.sidebar.expander("➕ New series", expanded=False):
        st.caption("Writes `config/series/<id>.json`. Adding a series is config, not code.")
        n_chars = st.number_input("How many characters?", min_value=1, max_value=8, value=2, step=1, key="ns_nchars")
        with st.form("new_series_form", clear_on_submit=False):
            series_id = st.text_input("series_id (slug, e.g. sky-pirates)")
            display_name = st.text_input("display name")
            logline = st.text_input("logline (one-sentence pitch)")
            premise = st.text_area("premise *", height=80)
            setting = st.text_input("setting")
            tone = st.text_input("tone")
            episode_format = st.text_area("episode_format", height=60)
            style_anchor = st.text_area("style_anchor * (global art-style tokens)", height=80)
            world_anchor = st.text_area("world_anchor (general world look, every shot)", height=60)

            char_inputs: list[tuple[str, str, str, str]] = []
            for i in range(int(n_chars)):
                st.markdown(f"**Character {i + 1}**")
                name = st.text_input("name", key=f"ns_c{i}_name")
                appearance = st.text_area("appearance_tokens *", key=f"ns_c{i}_app", height=60)
                personality = st.text_input("personality *", key=f"ns_c{i}_pers")
                voice = st.text_input("voice (Kokoro id, optional)", key=f"ns_c{i}_voice")
                char_inputs.append((name, appearance, personality, voice))

            submitted = st.form_submit_button("Create series")

        if not submitted:
            return

        series_id = series_id.strip()
        if not series_id:
            st.error("series_id is required.")
            return
        if series_id in list_series():
            st.error(f"series '{series_id}' already exists.")
            return

        characters = [
            Character(
                name=name.strip(),
                appearance_tokens=appearance.strip(),
                personality=personality.strip(),
                voice=voice.strip() or None,
            )
            for (name, appearance, personality, voice) in char_inputs
            if name.strip()
        ]
        try:
            bible = SeriesBible(
                series_id=series_id,
                premise=premise.strip(),
                style_anchor=style_anchor.strip(),
                characters=characters,
                world_anchor=world_anchor.strip() or None,
                display_name=display_name.strip() or None,
                logline=logline.strip() or None,
                setting=setting.strip() or None,
                tone=tone.strip() or None,
                episode_format=episode_format.strip() or None,
            )
        except Exception as e:
            st.error(f"Invalid series bible: {e}")
            return

        save_series_bible(bible)
        st.session_state["series"] = series_id
        st.success(f"Created series '{series_id}'. Next: add character reference images + run establish_characters.")
        st.rerun()


# --------------------------------------------------------------------------- sidebar: generate


def generate_panel(settings: Settings, series_id: str) -> None:
    st.sidebar.markdown("### ➕ New episode")
    prompt = st.sidebar.text_input("one-line prompt", key="gen_prompt", placeholder="leave empty to continue the arc")
    until = st.sidebar.selectbox("run through stage", STAGES, index=len(STAGES) - 1, key="gen_until")
    col_a, col_b = st.sidebar.columns(2)
    do_prompt = col_a.button("Generate", width="stretch", disabled=not prompt.strip())
    do_continue = col_b.button("Continue arc", width="stretch")

    if do_prompt or do_continue:
        args = ["src.pipeline.orchestrator", "--series", series_id, "--until", until]
        args += ["--prompt", prompt.strip()] if do_prompt else ["--continue"]
        ok = run_module(args, f"generate ({'prompt' if do_prompt else 'continue'}) → {until}")
        if ok:
            eps = list_episodes(settings, series_id)
            if eps:
                st.session_state[f"episode::{series_id}"] = eps[-1]
        st.rerun()


# --------------------------------------------------------------------------- QC rendering


def render_qc_report(report: dict[str, Any]) -> None:
    if report.get("passed"):
        st.success("QC: PASS")
    else:
        st.error("QC: FAIL")
    for c in report.get("checks", []):
        icon = "✅" if c["passed"] else ("⚠️" if not c["blocking"] else "❌")
        suffix = "" if c["blocking"] else "  _(optional)_"
        st.markdown(f"{icon} **{c['name']}** — {c['detail']}{suffix}")


# --------------------------------------------------------------------------- episode tabs


def tab_preview(settings: Settings, episode: Episode, episode_dir: Path) -> None:
    final = episode_dir / "final.mp4"
    left, right = st.columns([2, 3])

    with left:
        if final.exists():
            st.video(final.read_bytes())
        else:
            st.info("No final.mp4 yet — run the pipeline through `assemble`.")
        if st.button("🔁 Re-render video (assemble + QC)", disabled=not (episode_dir / "images").exists()):
            ok = run_module(
                ["src.pipeline.orchestrator", "--series", episode.series_id, "--episode", episode.episode_id,
                 "--force", "assemble", "qc", "--until", "qc"],
                "re-render (assemble + qc)",
            )
            st.rerun()

    with right:
        st.subheader("QC report")
        report = load_qc_report(episode_dir)
        if st.button("Run QC"):
            report = qc.run_qc(settings, episode, episode_dir)
        if report:
            render_qc_report(report)
        else:
            st.caption("No QC report yet — click **Run QC** (needs final.mp4).")

    st.divider()
    st.subheader("Caption")
    caption_file = episode_dir / "caption.txt"
    if caption_file.exists():
        st.code(caption_file.read_text(), language=None)
    else:
        st.caption("caption.txt is written by the assemble stage.")


def tab_images(settings: Settings, episode: Episode, episode_dir: Path) -> None:
    images_dir = episode_dir / "images"
    st.caption("Re-roll draws a fresh random seed for that one shot. Then **Re-render video** to rebuild final.mp4.")
    cols_per_row = 3
    for row_start in range(0, len(episode.scenes), cols_per_row):
        row = episode.scenes[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, scene in zip(cols, row):
            with col:
                img = images_dir / f"scene_{scene.id:02d}.png"
                if img.exists():
                    st.image(img.read_bytes(), caption=f"Scene {scene.id}")
                else:
                    st.warning(f"Scene {scene.id}: not rendered")
                with st.popover(f"ℹ️ Scene {scene.id}", width="stretch"):
                    st.caption(f"**location:** {scene.location or '—'}")
                    st.caption(f"**action:** {scene.action or '—'}")
                    st.caption(scene.image_prompt)
                if st.button("🔄 Re-roll", key=f"reroll_{scene.id}", width="stretch"):
                    run_module(
                        ["src.pipeline.images", "--episode", episode.episode_id, "--reroll", str(scene.id)],
                        f"re-roll scene {scene.id}",
                    )
                    st.rerun()


def tab_script(episode: Episode) -> None:
    st.markdown(f"### {episode.title}")
    st.markdown(f"**Hook:** {episode.hook_text}")
    if episode.hook.prompt:
        st.caption(f"hook clip: {episode.hook.prompt}")
    st.markdown(f"**Characters:** {', '.join(episode.characters_present)}")
    st.markdown(f"**Cliffhanger:** {episode.cliffhanger_text}")

    rows = [
        {
            "scene": s.id,
            "dur": s.duration_sec,
            "mood": s.mood,
            "intensity": s.intensity,
            "location": s.location,
            "action": s.action,
            "narration": s.narration_text,
        }
        for s in episode.scenes
    ]
    st.dataframe(rows, width="stretch", hide_index=True)
    st.caption(f"Total duration (hook + scenes): {episode.total_duration_sec:.1f}s")
    with st.expander("raw episode.json"):
        st.json(episode.model_dump())


def tab_review(settings: Settings, episode: Episode, episode_dir: Path) -> None:
    review = load_review(episode_dir)
    if review.get("approved"):
        st.success("Status: APPROVED")
    elif review.get("rejected"):
        st.error(f"Status: REJECTED — {review.get('note', '')}")
    else:
        st.info("Status: pending review")

    report = load_qc_report(episode_dir)
    qc_ok = bool(report and report.get("passed"))
    if report and not qc_ok:
        st.warning("QC is not currently passing — review the QC tab before approving.")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("✅ Approve → ready_to_post", width="stretch"):
            fresh = qc.run_qc(settings, episode, episode_dir)
            review.update(approved=True, rejected=False)
            save_review(episode_dir, review)
            if not fresh.get("passed"):
                st.warning("Approved despite QC failures.")
            try:
                dest = tiktok_stub.publish(settings, episode_dir)
                st.success(f"Published → {dest}")
            except NotImplementedError:
                st.info("Approved. Copy to ready_to_post/ is wired up in M9 (tiktok_stub).")
            st.rerun()
    with col_b:
        note = st.text_input("rejection note", key="reject_note")
        if st.button("🚫 Reject", width="stretch"):
            review.update(rejected=True, approved=False, note=note)
            save_review(episode_dir, review)
            st.rerun()


# --------------------------------------------------------------------------- main


def render_stage_status(state: dict[str, bool]) -> None:
    cols = st.columns(len(STAGES))
    for col, stage in zip(cols, STAGES):
        done = state.get(stage, False)
        col.markdown(f"{'✅' if done else '⬜️'}<br><span style='font-size:0.75em'>{stage}</span>", unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="slop-factory review", layout="wide")
    settings = load_settings()

    st.sidebar.title("🏭 slop-factory")
    series = list_series()
    new_series_form()

    if not series:
        st.title("slop-factory — review panel")
        st.info("No series yet. Use **➕ New series** in the sidebar to create one.")
        return

    series_id = st.sidebar.selectbox("Series", series, key="series")
    generate_panel(settings, series_id)

    episodes = list_episodes(settings, series_id)
    st.sidebar.divider()
    if episodes:
        episode_id = st.sidebar.selectbox("Episode", episodes, key=f"episode::{series_id}")
    else:
        episode_id = None
        st.sidebar.caption("No episodes yet — generate one above.")

    render_last_run()

    try:
        bible = load_series_bible(series_id)
    except Exception:
        bible = None
    st.title((bible.display_name if bible and bible.display_name else series_id))
    if bible and bible.logline:
        st.caption(bible.logline)

    if not episode_id:
        st.info("Generate an episode from the sidebar to start reviewing.")
        return

    episode_dir = settings.episodes_dir() / episode_id
    hdr, action = st.columns([5, 1])
    hdr.subheader(episode_id)
    with action.popover("🗑 Delete", width="stretch"):
        st.warning(f"Delete **{episode_id}** and roll the series plot back to before it was generated? This can't be undone.")
        if st.button("Confirm delete", key=f"confirm_delete::{episode_id}"):
            delete_episode(settings, series_id, episode_id)
            st.session_state.pop(f"episode::{series_id}", None)
            st.session_state["last_run"] = {
                "label": f"deleted {episode_id}",
                "ok": True,
                "code": 0,
                "out": f"removed {episode_id}; series plot_state rolled back",
            }
            st.rerun()
    render_stage_status(load_state(episode_dir))

    episode = load_episode(episode_dir)
    if episode is None:
        st.warning("This episode has no valid `episode.json` yet (script stage not complete).")
        return

    preview, images, script, review = st.tabs(["▶ Preview & QC", "🖼 Images", "📝 Script", "✅ Review"])
    with preview:
        tab_preview(settings, episode, episode_dir)
    with images:
        tab_images(settings, episode, episode_dir)
    with script:
        tab_script(episode)
    with review:
        tab_review(settings, episode, episode_dir)


main()
