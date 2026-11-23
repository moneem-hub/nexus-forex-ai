"""
ONE-TIME: wire utils/session.py into the app and restore the latest saved signal on the New Prediction page.
Run from the project root (commit first, so `git checkout .` undoes it):   python apply_session_patches.py
Each file is checked before it is changed; anything unexpected is skipped and reported, and re-running is safe.
"""
from pathlib import Path

PATCHES = [
    ("app.py", "restore_login",
     "st.session_state.setdefault('auth_page', 'login')\n",
     "st.session_state.setdefault('auth_page', 'login')\n\n"
     "# Keep users signed in across browser refreshes, with an inactivity timeout (utils/session.py)\n"
     "from utils.session import init_sessions, restore_login\n"
     "init_sessions()\n"
     "restore_login()\n"),
    ("app.py", "flash",
     "if not st.session_state.logged_in:\n    if st.session_state.auth_page == 'signup':\n",
     "if not st.session_state.logged_in:\n"
     "    _flash = st.session_state.pop('flash', None)          # e.g. 'session ended after 30 minutes of inactivity'\n"
     "    if _flash:\n        st.warning(_flash)\n"
     "    if st.session_state.auth_page == 'signup':\n"),
    ("components/login.py", "start_session",
     "                st.session_state.auth_page = 'login'\n                st.rerun()\n",
     "                st.session_state.auth_page = 'login'\n"
     "                from utils.session import start_session\n"
     "                start_session(username)\n"
     "                st.rerun()\n"),
    ("components/sidebar.py", "end_session",
     "            st.session_state.clear()   # sari session state saaf karo\n",
     "            from utils.session import end_session\n"
     "            end_session()              # delete the saved login so the old URL stops working\n"
     "            st.session_state.clear()   # sari session state saaf karo\n"),
    ("tabs/prediction.py", "restored from history",
     "                st.markdown(_no_signal_card(status), unsafe_allow_html=True)\n",
     "                st.markdown(_no_signal_card(status), unsafe_allow_html=True)\n"
     "        else:\n"
     "            # After a refresh or re-login the last scan is gone from session memory: show the latest SAVED signal for this pair\n"
     "            _saved = [h for h in st.session_state.get(\"history\", []) if h.get(\"Pair\") == pair_label]\n"
     "            if _saved:\n"
     "                _h = max(_saved, key=lambda r: str(r[\"Timestamp\"]))\n"
     "                try:\n"
     "                    _risk = abs(float(_h[\"Entry\"]) - float(_h[\"Stop Loss\"]))\n"
     "                    _tp1  = float(_h[\"Entry\"]) + (1.5 * _risk if _h[\"Signal\"] == \"BUY\" else -1.5 * _risk)   # the card's TP1 = 1.5R\n"
     "                    _sig = {\"direction\": _h[\"Signal\"], \"rr\": float(str(_h[\"R:R\"]).split(\":\")[1]), \"session_label\": \"saved signal\",\n"
     "                            \"timestamp\": _h[\"Timestamp\"], \"entry\": float(_h[\"Entry\"]), \"sl\": float(_h[\"Stop Loss\"]),\n"
     "                            \"tp\": float(_h[\"Take Profit\"]), \"tp1\": _tp1, \"pair\": pair_label}\n"
     "                    st.markdown(\"<br>\", unsafe_allow_html=True)\n"
     "                    st.markdown(f\"<div style='font-family:Roboto,sans-serif;font-size:.75rem;color:#4A6699;margin-bottom:6px;'>\"\n"
     "                                f\"Latest saved signal for {pair_label} (restored from history)</div>\", unsafe_allow_html=True)\n"
     "                    st.markdown(_signal_card(_sig), unsafe_allow_html=True)\n"
     "                except (KeyError, ValueError, IndexError):\n"
     "                    pass\n"),
]

if not Path("utils/session.py").exists():
    raise SystemExit("utils/session.py is missing: copy it into the utils folder first.")
for fname, marker, old, new in PATCHES:
    p = Path(fname)
    src = p.read_text(encoding="utf-8")
    if marker in src:
        print(f"skip   {fname}: '{marker}' already present")
    elif src.count(old) != 1:
        print(f"SKIPPED {fname}: expected text not found exactly once (your file differs). Tell me and I will give you the manual edit.")
    else:
        p.write_text(src.replace(old, new), encoding="utf-8")
        print(f"patched {fname}")
