"""Optional Streamlit entry. Prefer `quasar2 dashboard` (stdlib HTML) if Streamlit is absent."""

from __future__ import annotations


def main() -> None:
    try:
        import streamlit as st
    except ImportError as error:
        raise RuntimeError("streamlit not installed; run `quasar2 dashboard` instead") from error

    from quasar2.observability import default_rescue_dir, load_run

    loaded = load_run(default_rescue_dir())
    st.title("QUASAR2 Research Cockpit")
    if not loaded.get("available"):
        st.warning(loaded.get("reason"))
        return
    manifest = loaded["manifest"]
    st.json({"gates": manifest.get("gates"), "n": manifest.get("n_queries")})
    st.caption("This page reads artifacts. It does not recompute Rescue.")
