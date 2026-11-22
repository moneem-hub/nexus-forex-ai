def get_css() -> str:
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Anton&family=Roboto:wght@300;400;500;700&family=JetBrains+Mono:wght@300;400;500;600&display=swap');

/* ══════════════════════════════════════════════════════════════
   CSS VARIABLES
══════════════════════════════════════════════════════════════ */
:root {
    --white:   #FFFFFF;
    --navy:    #111844;
    --blue:    #7AAACE;
    --lite:    #9CD5FF;

    /* Sidebar (dark navy) */
    --sb:      #111844;
    --sb2:     #18215E;
    --sb3:     #1F2B78;
    --sb4:     #283592;
    --sbt1:    #FFFFFF;
    --sbt2:    #9CD5FF;
    --sbt3:    #7AAACE;
    --sbt4:    #4A6699;

    /* Main content (white) */
    --bg:      #F0F4FF;
    --card:    #FFFFFF;
    --surface: #E8EEFF;
    --bd:      #D4DEFA;
    --bd2:     #B0C4EC;

    /* Text on white */
    --t1: #111844;
    --t2: #233070;
    --t3: #7AAACE;
    --t4: #9CD5FF;
    --t5: #D4DEFA;

    /* Status */
    --green:   #059669;
    --greenl:  #ECFDF5;
    --green2:  #D1FAE5;
    --red:     #DC2626;
    --redl:    #FFF5F5;
    --red2:    #FEE2E2;
    --amber:   #D97706;
    --ambl:    #FFFBEB;
    --amber2:  #FDE68A;
}

/* ══════════════════════════════════════════════════════════════
   GLOBAL RESET
══════════════════════════════════════════════════════════════ */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body, [class*="css"] {
    font-family: 'Roboto', sans-serif;
    background: var(--bg);
    color: var(--t2);
}
#MainMenu, footer, header { visibility: hidden; }
.stApp { background: var(--bg); }
.block-container { padding: 0 2rem 2rem 2rem !important; max-width: none !important; }

/* ══════════════════════════════════════════════════════════════
   SIDEBAR — FORCE VISIBLE + DARK NAVY THEME
══════════════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    transform: none !important;
    translate: 0px !important;
    min-width: 280px !important;
    width: 280px !important;
    max-width: 280px !important;
    position: relative !important;
    left: 0 !important;
    flex-shrink: 0 !important;
    background: var(--sb) !important;
    border-right: 1px solid var(--sb3) !important;
    padding-top: 0 !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
    width: 100% !important;
}
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    background: var(--sb2) !important;
    border: 1px solid var(--sb3) !important;
    border-left: none !important;
    border-radius: 0 8px 8px 0 !important;
    z-index: 9999 !important;
}
[data-testid="collapsedControl"] svg { stroke: var(--sbt4) !important; }
[data-testid="collapsedControl"]:hover svg { stroke: var(--sbt2) !important; }

/* ══════════════════════════════════════════════════════════════
   SIDEBAR BRAND
══════════════════════════════════════════════════════════════ */
.sb-wrap { padding-bottom: 12px; border-bottom: 1px solid var(--sb3); margin-bottom: 2px; }
.sb-top-line { height: 3px; background: linear-gradient(90deg, var(--navy) 0%, var(--blue) 50%, var(--lite) 100%); }
.sb-inner   { padding: 16px 18px 0; }
.sb-logo-row { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.sb-icon {
    width: 42px; height: 42px;
    background: linear-gradient(135deg, var(--sb3) 0%, var(--sb4) 100%);
    border: 1px solid rgba(156,213,255,.2);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.sb-brand-name {
    font-family: 'Anton', sans-serif;
    font-size: 1.25rem;
    color: var(--sbt1);
    line-height: 1;
    letter-spacing: 0.04em;
}
.sb-brand-tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: .52rem;
    color: var(--sbt4);
    letter-spacing: .18em;
    text-transform: uppercase;
    margin-top: 3px;
}
.sb-version {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(156,213,255,.08);
    border: 1px solid rgba(156,213,255,.18);
    border-radius: 4px;
    padding: 2px 7px;
    font-family: 'JetBrains Mono', monospace;
    font-size: .52rem;
    color: var(--sbt2);
    letter-spacing: .15em;
    text-transform: uppercase;
    margin-top: 6px;
    display: inline-block;
}

/* ══════════════════════════════════════════════════════════════
   SIDEBAR SECTION LABEL
══════════════════════════════════════════════════════════════ */
.sb-sec {
    display: flex; align-items: center; gap: 8px;
    padding: 14px 18px 8px;
}
.sb-sec-icon { flex-shrink: 0; opacity: .5; }
.sb-sec-t {
    font-family: 'Roboto', sans-serif;
    font-size: .64rem; font-weight: 700;
    color: var(--sbt4);
    letter-spacing: .2em; text-transform: uppercase;
    white-space: nowrap;
}
.sb-sec-l { flex: 1; height: 1px; background: var(--sb3); }

/* ══════════════════════════════════════════════════════════════
   SIDEBAR PAIR BOX
══════════════════════════════════════════════════════════════ */
.pair-box {
    margin: 4px 14px 14px;
    background: var(--sb2);
    border: 1px solid var(--sb3);
    border-radius: 12px;
    padding: 12px 16px;
    display: flex; align-items: center; justify-content: space-between;
}
.pair-lbl {
    font-family: 'JetBrains Mono', monospace;
    font-size: .52rem; color: var(--sbt4);
    letter-spacing: .18em; text-transform: uppercase; margin-bottom: 3px;
}
.pair-val {
    font-family: 'Anton', sans-serif;
    font-size: 1.1rem; color: var(--sbt2);
    letter-spacing: .04em;
}
.pair-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: .54rem; font-weight: 600;
    color: var(--sbt2);
    background: rgba(156,213,255,.1);
    border: 1px solid rgba(156,213,255,.2);
    border-radius: 6px;
    padding: 4px 9px; letter-spacing: .1em;
}

/* ══════════════════════════════════════════════════════════════
   SIDEBAR NEWS CARDS
══════════════════════════════════════════════════════════════ */
.sb-card {
    background: var(--sb2);
    border: 1px solid var(--sb3);
    border-radius: 10px;
    margin: 0 12px 8px;
    padding: 12px 14px;
    transition: background .15s, border-color .15s;
    cursor: default;
    position: relative;
    overflow: hidden;
}
.sb-card:hover { background: var(--sb3); border-color: var(--sb4); }
.sb-card-high { border-left: 3px solid #F85149; }
.sb-card-med  { border-left: 3px solid #E3B341; }
.sb-card-low  { border-left: 3px solid #3FB950; }
.sb-card-row  { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; margin-bottom: 5px; }
.sb-card-name {
    font-family: 'Roboto', sans-serif;
    font-size: .82rem; font-weight: 700; color: var(--sbt1);
}
.sb-card-sub {
    font-family: 'Roboto', sans-serif;
    font-size: .68rem; font-weight: 500; color: var(--sbt3);
    margin-bottom: 5px;
}
.sb-card-desc {
    font-family: 'Roboto', sans-serif;
    font-size: .68rem; color: var(--sbt4);
    line-height: 1.5;
    margin-bottom: 8px;
}
.sb-card-foot {
    display: flex; align-items: center; gap: 6px;
}
.sb-imp-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: .5rem; font-weight: 600;
    letter-spacing: .12em; text-transform: uppercase;
    padding: 2px 7px; border-radius: 4px;
}
.sb-imp-h { color: #F85149; background: rgba(248,81,73,.12); border: 1px solid rgba(248,81,73,.25); }
.sb-imp-m { color: #E3B341; background: rgba(227,179,65,.12); border: 1px solid rgba(227,179,65,.25); }
.sb-imp-l { color: #3FB950; background: rgba(63,185,80,.12); border: 1px solid rgba(63,185,80,.25); }
.sb-imp-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.dot-h { background: #F85149; box-shadow: 0 0 5px rgba(248,81,73,.5); }
.dot-m { background: #E3B341; box-shadow: 0 0 5px rgba(227,179,65,.5); }
.dot-l { background: #3FB950; box-shadow: 0 0 5px rgba(63,185,80,.5); }

/* ══════════════════════════════════════════════════════════════
   BUTTONS
══════════════════════════════════════════════════════════════ */
.stButton > button {
    background: var(--card);
    border: 1px solid var(--bd);
    color: var(--t2);
    font-family: 'Roboto', sans-serif;
    font-weight: 500;
    border-radius: 8px;
    font-size: .82rem;
    transition: all .15s ease;
    padding: 8px 16px;
    cursor: pointer;
}
.stButton > button:hover {
    background: var(--surface);
    border-color: var(--blue);
    color: var(--navy);
    box-shadow: 0 2px 8px rgba(17,24,68,.1);
    transform: translateY(-1px);
}
/* Primary CTA */
.cta-btn > button {
    background: var(--navy) !important;
    border-color: var(--navy) !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    padding: 13px 22px !important;
    font-size: .88rem !important;
    border-radius: 10px !important;
    letter-spacing: .02em !important;
    box-shadow: 0 4px 14px rgba(17,24,68,.3) !important;
}
.cta-btn > button:hover {
    background: #192580 !important;
    box-shadow: 0 6px 20px rgba(17,24,68,.4) !important;
    transform: translateY(-2px) !important;
}
/* Sidebar buttons stay dark */
section[data-testid="stSidebar"] .stButton > button {
    background: var(--sb2) !important;
    border-color: var(--sb3) !important;
    color: var(--sbt3) !important;
    font-family: 'Roboto', sans-serif !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--sb3) !important;
    border-color: var(--sbt2) !important;
    color: var(--sbt1) !important;
    transform: translateY(-1px) !important;
}
/* Calendar CTA in sidebar */
.sb-cal-btn > button {
    background: linear-gradient(135deg, var(--sb3) 0%, var(--sb4) 100%) !important;
    border-color: rgba(156,213,255,.25) !important;
    color: var(--sbt2) !important;
    font-weight: 700 !important;
    font-size: .8rem !important;
    letter-spacing: .03em !important;
}
.sb-cal-btn > button:hover {
    background: linear-gradient(135deg, var(--sb4) 0%, #324AAA 100%) !important;
    border-color: rgba(156,213,255,.5) !important;
    color: var(--sbt1) !important;
    box-shadow: 0 4px 12px rgba(156,213,255,.15) !important;
}

/* ══════════════════════════════════════════════════════════════
   FORM CONTROLS
══════════════════════════════════════════════════════════════ */
.stSelectbox > div > div {
    background: var(--card) !important;
    border: 1.5px solid var(--bd) !important;
    color: var(--t1) !important;
    border-radius: 8px !important;
    font-size: .84rem !important;
    font-family: 'Roboto', sans-serif !important;
    cursor: pointer !important;
}
.stSelectbox > div > div:hover {
    border-color: var(--blue) !important;
    cursor: pointer !important;
}
.stSelectbox [data-baseweb="select"] { cursor: pointer !important; }
.stSelectbox [data-baseweb="select"] > div { cursor: pointer !important; }
section[data-testid="stSidebar"] .stSelectbox > div > div {
    background: var(--sb2) !important;
    border-color: var(--sb3) !important;
    color: var(--sbt1) !important;
    cursor: pointer !important;
}
section[data-testid="stSidebar"] .stSelectbox > div > div:hover {
    border-color: var(--sbt2) !important;
}
.stTextInput > div > div > input {
    background: var(--card) !important;
    border: 1.5px solid var(--bd2) !important;
    color: var(--t1) !important;
    border-radius: 10px !important;
    font-size: .86rem !important;
    font-family: 'Roboto', sans-serif !important;
    padding: 12px 16px !important;
    transition: all .15s !important;
}
.stTextInput > div > div > input:focus {
    border-color: var(--navy) !important;
    box-shadow: 0 0 0 3px rgba(17,24,68,.1) !important;
    outline: none !important;
}
.stTextInput > div > div > input::placeholder { color: var(--t5) !important; }

/* ══════════════════════════════════════════════════════════════
   TABS
══════════════════════════════════════════════════════════════ */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 2px solid var(--bd) !important;
    gap: 0 !important;
    padding: 0 !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Roboto', sans-serif !important;
    font-size: .84rem !important;
    font-weight: 500 !important;
    color: var(--t3) !important;
    border-radius: 0 !important;
    padding: 13px 24px !important;
    border-bottom: 2px solid transparent !important;
    background: transparent !important;
    transition: all .15s !important;
    cursor: pointer !important;
    letter-spacing: .01em !important;
    margin-bottom: -2px !important;
}
.stTabs [aria-selected="true"] {
    color: var(--navy) !important;
    border-bottom: 2px solid var(--navy) !important;
    font-weight: 700 !important;
    background: transparent !important;
}
.stTabs [data-baseweb="tab"]:hover {
    color: var(--t2) !important;
    background: rgba(17,24,68,.04) !important;
}

/* ══════════════════════════════════════════════════════════════
   DASHBOARD HEADER
══════════════════════════════════════════════════════════════ */
.dash-hdr {
    display: flex; align-items: flex-end; justify-content: space-between;
    padding: 28px 0 24px;
    border-bottom: 2px solid var(--bd);
}
.dash-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: .6rem; font-weight: 600;
    color: var(--blue);
    letter-spacing: .3em; text-transform: uppercase;
    margin-bottom: 8px;
    display: flex; align-items: center; gap: 8px;
}
.ey-dot { width: 6px; height: 6px; background: var(--navy); border-radius: 50%; }
.dash-title {
    font-family: 'Anton', sans-serif;
    font-size: 2.1rem;
    color: var(--navy);
    letter-spacing: .02em;
    line-height: 1;
}
.dash-title-accent { color: var(--blue); }
.dash-meta { text-align: right; }
.dash-meta-lbl {
    font-family: 'JetBrains Mono', monospace;
    font-size: .55rem; color: var(--t4);
    letter-spacing: .2em; text-transform: uppercase; margin-bottom: 5px;
}
.dash-meta-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: .86rem; font-weight: 600;
    color: var(--navy); letter-spacing: .04em;
}

/* ══════════════════════════════════════════════════════════════
   LIVE STRIP
══════════════════════════════════════════════════════════════ */
.live-strip {
    display: inline-flex; align-items: center; gap: 10px;
    padding: 6px 14px;
    background: var(--greenl);
    border: 1px solid #A7F3D0;
    border-radius: 8px;
    margin: 16px 0 20px;
}
.live-dot { width: 7px; height: 7px; background: var(--green); border-radius: 50%; animation: pulseG 1.8s infinite; }
@keyframes pulseG { 0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(5,150,105,.4);}50%{opacity:.8;box-shadow:0 0 0 5px rgba(5,150,105,0);} }
.live-lbl  { font-family: 'JetBrains Mono', monospace; font-size: .6rem; color: var(--green); letter-spacing: .2em; text-transform: uppercase; font-weight: 600; }
.live-pair { font-family: 'JetBrains Mono', monospace; font-size: .6rem; font-weight: 700; color: var(--navy); letter-spacing: .08em; }

/* ══════════════════════════════════════════════════════════════
   PRICE CARDS
══════════════════════════════════════════════════════════════ */
.price-card {
    background: var(--card);
    border: 1px solid var(--bd);
    border-radius: 14px;
    padding: 18px 20px;
    position: relative; overflow: hidden;
    box-shadow: 0 2px 8px rgba(17,24,68,.06), 0 1px 2px rgba(17,24,68,.04);
    transition: all .2s ease;
    cursor: default;
}
.price-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px;
}
.pc-navy::before  { background: var(--navy); }
.pc-gray::before  { background: var(--t5); }
.pc-green::before { background: var(--green); }
.pc-red::before   { background: var(--red); }
.pc-blue::before  { background: var(--blue); }
.price-card:hover {
    border-color: var(--blue);
    transform: translateY(-3px);
    box-shadow: 0 10px 30px rgba(17,24,68,.12);
}
.pc-label {
    font-family: 'Roboto', sans-serif;
    font-size: .66rem; font-weight: 700;
    color: var(--t3); text-transform: uppercase; letter-spacing: .15em; margin-bottom: 10px;
}
.pc-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.1rem; font-weight: 600; color: var(--t1);
    letter-spacing: .02em; line-height: 1;
}
.pc-change {
    font-family: 'JetBrains Mono', monospace;
    font-size: .66rem; font-weight: 600;
    margin-top: 7px; letter-spacing: .04em;
}
.pc-icon {
    position: absolute; top: 16px; right: 16px;
    font-size: 1.4rem; font-weight: 700; opacity: .05;
}
.up   { color: var(--green) !important; }
.down { color: var(--red) !important; }

/* ══════════════════════════════════════════════════════════════
   SECTION HEADER
══════════════════════════════════════════════════════════════ */
.sec-hdr {
    display: flex; align-items: center; gap: 12px;
    margin-bottom: 18px; padding-bottom: 14px;
    border-bottom: 2px solid var(--bd);
}
.sec-bar  { width: 4px; height: 18px; background: var(--navy); border-radius: 3px; flex-shrink: 0; }
.sec-txt  {
    font-family: 'Roboto', sans-serif;
    font-size: .72rem; font-weight: 700;
    color: var(--navy); letter-spacing: .18em; text-transform: uppercase;
}
.sec-line { flex: 1; height: 1px; background: var(--bd); }

/* ══════════════════════════════════════════════════════════════
   SIGNAL BOX
══════════════════════════════════════════════════════════════ */
.sig-box {
    border-radius: 16px; padding: 32px 28px;
    text-align: center; position: relative;
    overflow: hidden; margin: 18px 0;
    box-shadow: 0 4px 20px rgba(0,0,0,.08);
}
.sig-buy  { background: var(--greenl); border: 2px solid #A7F3D0; }
.sig-buy::before  { content:''; position:absolute; top:0;left:0;right:0; height:4px; background:var(--green); }
.sig-sell { background: var(--redl); border: 2px solid #FCA5A5; }
.sig-sell::before { content:''; position:absolute; top:0;left:0;right:0; height:4px; background:var(--red); }
.sig-dir {
    font-family: 'Anton', sans-serif;
    font-size: 3.2rem; line-height: 1; margin-bottom: 8px;
    letter-spacing: .04em;
}
.sig-buy  .sig-dir { color: #065F46; }
.sig-sell .sig-dir { color: #991B1B; }
.sig-sub {
    font-family: 'Roboto', sans-serif;
    font-size: .78rem; font-weight: 500;
    letter-spacing: .06em; margin-bottom: 18px;
}
.sig-buy  .sig-sub { color: var(--green); }
.sig-sell .sig-sub { color: var(--red); }
.conf-lbl { font-family: 'JetBrains Mono', monospace; font-size: .56rem; font-weight: 600; color: var(--t3); letter-spacing: .22em; text-transform: uppercase; margin-bottom: 8px; }
.conf-bg  { background: rgba(17,24,68,.06); border-radius: 6px; height: 8px; overflow: hidden; margin-bottom: 7px; }
.conf-fill { height: 100%; border-radius: 6px; }
.cf-buy  { background: linear-gradient(90deg, #6EE7B7, var(--green)); }
.cf-sell { background: linear-gradient(90deg, #FCA5A5, var(--red)); }
.conf-pct { font-family: 'Anton', sans-serif; font-size: 1.1rem; }
.sig-buy  .conf-pct { color: #065F46; }
.sig-sell .conf-pct { color: #991B1B; }

/* ══════════════════════════════════════════════════════════════
   TRADE PARAMS
══════════════════════════════════════════════════════════════ */
.tparams { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 14px; }
.tparam {
    background: var(--card);
    border: 1px solid var(--bd);
    border-radius: 12px;
    padding: 14px 16px;
    text-align: center;
    box-shadow: 0 1px 4px rgba(17,24,68,.06);
    transition: box-shadow .2s;
}
.tparam:hover { box-shadow: 0 4px 12px rgba(17,24,68,.12); }
.tp-lbl { font-family: 'Roboto', sans-serif; font-size: .64rem; font-weight: 700; color: var(--t3); text-transform: uppercase; letter-spacing: .14em; margin-bottom: 8px; }
.tp-val { font-family: 'JetBrains Mono', monospace; font-size: .95rem; font-weight: 600; color: var(--t1); }
.tp-entry { border-top: 3px solid var(--navy); }
.tp-sl    { border-top: 3px solid var(--red); }
.tp-sl  .tp-val { color: var(--red); }
.tp-tp    { border-top: 3px solid var(--green); }
.tp-tp  .tp-val { color: var(--green); }

/* ══════════════════════════════════════════════════════════════
   RR STRIP
══════════════════════════════════════════════════════════════ */
.rr-strip { display: flex; gap: 10px; margin-top: 12px; }
.rr-box {
    flex: 1; background: var(--surface);
    border: 1px solid var(--bd);
    border-radius: 10px; padding: 11px 14px; text-align: center;
}
.rr-lbl { font-family: 'Roboto', sans-serif; font-size: .62rem; font-weight: 700; color: var(--t3); text-transform: uppercase; letter-spacing: .14em; margin-bottom: 5px; }
.rr-val { font-family: 'JetBrains Mono', monospace; font-size: .88rem; font-weight: 700; color: var(--navy); }

/* ══════════════════════════════════════════════════════════════
   MODEL CARD
══════════════════════════════════════════════════════════════ */
.model-card {
    background: var(--card);
    border: 1px solid var(--bd);
    border-radius: 14px; padding: 22px;
    box-shadow: 0 2px 8px rgba(17,24,68,.06);
}
.model-hdr {
    display: flex; align-items: center; justify-content: space-between;
    padding-bottom: 14px; margin-bottom: 14px;
    border-bottom: 2px solid var(--bd);
}
.model-hdr-t {
    font-family: 'Roboto', sans-serif;
    font-size: .82rem; font-weight: 700; color: var(--t1);
}
.acc-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--green2); border: 1px solid #6EE7B7;
    border-radius: 20px; padding: 4px 11px;
    font-family: 'JetBrains Mono', monospace; font-size: .68rem; font-weight: 700;
    color: #065F46;
}
.acc-dot { width: 6px; height: 6px; background: var(--green); border-radius: 50%; animation: pulseG 2s infinite; }
.m-row { display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--bd); }
.m-row:last-child { border-bottom: none; }
.m-key { font-family: 'Roboto', sans-serif; font-size: .8rem; color: var(--t3); }
.m-val { font-family: 'JetBrains Mono', monospace; font-size: .76rem; font-weight: 500; color: var(--t2); }
.m-green { color: var(--green) !important; font-weight: 700 !important; }
.m-blue  { color: var(--navy) !important; font-weight: 700 !important; }

/* ══════════════════════════════════════════════════════════════
   DATAFRAME
══════════════════════════════════════════════════════════════ */
.stDataFrame { border-radius: 12px !important; overflow: hidden !important; border: 1px solid var(--bd) !important; box-shadow: 0 2px 8px rgba(17,24,68,.06) !important; }
div[data-testid="stDataFrameResizable"] table { background: var(--card) !important; font-family: 'JetBrains Mono', monospace !important; font-size: .76rem !important; }
div[data-testid="stDataFrameResizable"] th { background: var(--surface) !important; color: var(--t3) !important; font-size: .62rem !important; letter-spacing: .14em !important; text-transform: uppercase !important; border-bottom: 2px solid var(--bd) !important; font-family: 'Roboto', sans-serif !important; font-weight: 700 !important; padding: 12px 16px !important; }
div[data-testid="stDataFrameResizable"] td { color: var(--t2) !important; border-bottom: 1px solid var(--bd) !important; padding: 10px 16px !important; }

/* ══════════════════════════════════════════════════════════════
   EMPTY STATE
══════════════════════════════════════════════════════════════ */
.empty-box {
    text-align: center; padding: 60px 24px;
    border: 2px dashed var(--bd2);
    border-radius: 14px; background: var(--card);
}
.empty-ico  { font-size: 2.5rem; margin-bottom: 16px; opacity: .4; }
.empty-ttl  { font-family: 'Roboto', sans-serif; font-size: .92rem; font-weight: 700; color: var(--t3); margin-bottom: 7px; }
.empty-sub  { font-family: 'Roboto', sans-serif; font-size: .8rem; color: var(--t4); }

/* ══════════════════════════════════════════════════════════════
   STAT CARDS (history)
══════════════════════════════════════════════════════════════ */
.stat-card {
    background: var(--card); border: 1px solid var(--bd);
    border-radius: 14px; padding: 20px 22px; margin-bottom: 18px;
    box-shadow: 0 2px 8px rgba(17,24,68,.06);
    position: relative; overflow: hidden;
}
.stat-card::before { content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 3px; }
.stat-card-navy::before  { background: var(--navy); }
.stat-card-green::before { background: var(--green); }
.stat-card-red::before   { background: var(--red); }
.stat-card-purple::before { background: #7C3AED; }
.stat-lbl { font-family: 'Roboto', sans-serif; font-size: .62rem; font-weight: 700; color: var(--t3); text-transform: uppercase; letter-spacing: .18em; margin-bottom: 10px; }
.stat-val { font-family: 'Anton', sans-serif; font-size: 2.4rem; letter-spacing: .02em; line-height: 1; }

/* ══════════════════════════════════════════════════════════════
   LOGIN PAGE
══════════════════════════════════════════════════════════════ */
.login-bg {
    min-height: 100vh;
    background: linear-gradient(135deg, #080C2A 0%, #111844 45%, #162260 100%);
    display: flex; align-items: center; justify-content: center;
    position: relative; overflow: hidden;
}
.login-bg::before {
    content: ''; position: absolute; inset: 0;
    background-image: radial-gradient(circle at 20% 50%, rgba(122,170,206,.06) 0%, transparent 50%),
                      radial-gradient(circle at 80% 20%, rgba(156,213,255,.05) 0%, transparent 50%);
    pointer-events: none;
}
.login-card {
    background: rgba(24,33,94,.7);
    border: 1px solid rgba(156,213,255,.2);
    border-radius: 24px;
    overflow: hidden;
    width: 100%;
    backdrop-filter: blur(20px);
    box-shadow: 0 32px 100px rgba(0,0,0,.5), 0 0 0 1px rgba(156,213,255,.08);
}
.login-topbar { height: 3px; background: linear-gradient(90deg, var(--navy), var(--blue), var(--lite)); }
.login-body { padding: 36px; }
.login-brand-row {
    display: flex; align-items: center; gap: 16px; margin-bottom: 30px;
}
.login-brand-icon {
    width: 52px; height: 52px;
    background: linear-gradient(135deg, var(--sb3) 0%, var(--sb4) 100%);
    border: 1px solid rgba(156,213,255,.25);
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 4px 12px rgba(0,0,0,.3);
}
.login-brand-name {
    font-family: 'Anton', sans-serif;
    font-size: 1.6rem; color: #FFFFFF;
    letter-spacing: .04em; line-height: 1;
}
.login-brand-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: .54rem; color: var(--sbt4);
    letter-spacing: .18em; text-transform: uppercase; margin-top: 4px;
}
.login-divider { height: 1px; background: rgba(156,213,255,.1); margin: 0 0 26px; }
.login-hi   { font-family: 'Roboto', sans-serif; font-size: 1.1rem; font-weight: 700; color: #E8EEFF; margin-bottom: 4px; }
.login-hi-s { font-family: 'JetBrains Mono', monospace; font-size: .6rem; color: var(--sbt4); letter-spacing: .15em; text-transform: uppercase; margin-bottom: 26px; }
.login-lbl  { font-family: 'JetBrains Mono', monospace; font-size: .58rem; font-weight: 600; color: var(--sbt3); letter-spacing: .2em; text-transform: uppercase; display: block; margin-bottom: 7px; }
.login-foot { display: flex; align-items: center; justify-content: space-between; padding: 16px 36px 22px; border-top: 1px solid rgba(156,213,255,.08); margin-top: 8px; }
.login-fl   { font-family: 'JetBrains Mono', monospace; font-size: .52rem; color: rgba(255,255,255,.2); letter-spacing: .1em; text-transform: uppercase; }
.login-sts  { display: flex; align-items: center; gap: 6px; font-family: 'JetBrains Mono', monospace; font-size: .52rem; color: rgba(255,255,255,.3); }
.sts-dot    { width: 6px; height: 6px; background: #3FB950; border-radius: 50%; animation: pulseG 2s infinite; }

/* Login page input overrides (dark theme) */
.login-inputs .stTextInput > div > div > input {
    background: rgba(17,24,68,.6) !important;
    border: 1.5px solid rgba(156,213,255,.2) !important;
    color: #edeef1 !important;
    border-radius: 10px !important;
    font-size: .86rem !important;
    font-family: 'Roboto', sans-serif !important;
    padding: 13px 16px !important;
}
.login-inputs .stTextInput > div > div > input:focus {
    border-color: var(--lite) !important;
    box-shadow: 0 0 0 3px rgba(156,213,255,.15) !important;
}
.login-inputs .stTextInput > div > div > input::placeholder { color: rgba(156,213,255,.25) !important; }
.login-inputs .cta-btn > button {
    background: linear-gradient(135deg, var(--sb3) 0%, var(--sb4) 100%) !important;
    border-color: rgba(156,213,255,.3) !important;
    color: #FFFFFF !important;
    font-family: 'Anton', sans-serif !important;
    font-size: 1rem !important;
    letter-spacing: .06em !important;
    padding: 14px 22px !important;
    box-shadow: 0 4px 16px rgba(0,0,0,.3) !important;
}
.login-inputs .cta-btn > button:hover {
    background: linear-gradient(135deg, var(--sb4) 0%, #3246AA 100%) !important;
    box-shadow: 0 6px 24px rgba(156,213,255,.2) !important;
}

/* ══════════════════════════════════════════════════════════════
   CALENDAR TAB
══════════════════════════════════════════════════════════════ */
.cal-container {
    background: var(--card);
    border: 1px solid var(--bd);
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(17,24,68,.08);
}

/* ══════════════════════════════════════════════════════════════
   MISC
══════════════════════════════════════════════════════════════ */
hr { border-color: var(--bd) !important; margin: 12px 0 !important; }
.stAlert { border-radius: 10px !important; font-size: .84rem !important; font-family: 'Roboto', sans-serif !important; }
.stSpinner > div { border-top-color: var(--navy) !important; }
.stDownloadButton > button {
    background: var(--card) !important; border: 1.5px solid var(--bd2) !important;
    color: var(--t3) !important; border-radius: 8px !important;
    font-size: .8rem !important; font-family: 'Roboto', sans-serif !important;
    font-weight: 500 !important;
}
.stDownloadButton > button:hover { border-color: var(--navy) !important; color: var(--navy) !important; }
/* Hide zero-height iframes used for JS injection */
iframe[height="0"] { display: none !important; }
</style>
"""
