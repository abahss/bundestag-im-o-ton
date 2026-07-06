import calendar as cal_module
import os
import re
import requests
import streamlit as st
from datetime import date, datetime
from itertools import groupby
from rapidfuzz import fuzz

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


st.markdown("""
<style>
header.stAppHeader { background-color: transparent; }
section.stMain .block-container { padding-top: 0rem; z-index: 1; max-width: calc(50vw + 23rem) !important; }
[data-testid="stPageLink"] p { white-space: normal !important; word-break: break-word; }
/* Calendar buttons: remove bubble */
div[data-testid="stButton"] button {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 2px 4px !important;
    min-height: 0 !important;
    font-size: 0.82rem !important;
    color: #023047 !important;
    border-radius: 4px !important;
}
/* Session days: light blue */
div[data-testid="stButton"] button[kind="secondary"]:not(:disabled) {
    background: #D6EEF7 !important;
}
/* Selected day */
div[data-testid="stButton"] button[kind="primary"] {
    background: #219EBC !important;
    color: white !important;
}
/* Search input: no fill */
div[data-testid="stTextInput"] input,
div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextInput"] > div,
div[data-testid="stTextInput"] > div > div {
    background: transparent !important;
    background-color: transparent !important;
}
/* Summary button inside expanders: outlined, no fill */
details div[data-testid="stButton"] button[kind="secondary"]:not(:disabled) {
    background: transparent !important;
    border: 1.5px solid #219EBC !important;
    color: #219EBC !important;
    padding: 5px 14px !important;
    font-size: 0.85rem !important;
}
/* Non-session days: muted */
div[data-testid="stButton"] button:disabled {
    opacity: 0.3 !important;
    background: transparent !important;
}
</style>""", unsafe_allow_html=True)

st.write("<h1 style='text-align: center;'>Was im Bundestag wirklich gesagt wird.</h1>", unsafe_allow_html=True)
st.write(
    "Bundestagsdebatten sind öffentlich – aber kaum jemand liest Plenarprotokolle. "
    "Bundestag im O-Ton macht sie zugänglich: Für jede Sitzung und jeden Tagesordnungspunkt findest du eine neutrale Zusammenfassung des Themas "
    "sowie die Position jeder Partei, belegt mit direkten Zitaten aus dem Originalprotokoll. "
    "Ein Klick genügt, um das Zitat im PDF nachzuschlagen."
)
st.write(
    "Keine Meinungsmache, keine Verkürzung – nur das, was tatsächlich gesagt wurde. "
    "So verstehst du in wenigen Minuten, worüber debattiert wurde und wer wofür steht."
)

@st.cache_data(ttl=None)
def fetch_all_topics():
    try:
        return requests.get(f"{BACKEND_URL}/all_topics").json()
    except Exception:
        return []

all_topics = fetch_all_topics()

# Parse session dates for the calendar
session_dates = set()
for t in all_topics:
    try:
        session_dates.add(datetime.strptime(t["date"], "%d.%m.%Y").date())
    except ValueError:
        pass

# Initialise calendar state to the month of the latest session
if "cal_year" not in st.session_state or "cal_month" not in st.session_state:
    anchor = max(session_dates) if session_dates else date.today()
    st.session_state.cal_year = anchor.year
    st.session_state.cal_month = anchor.month
if "cal_selected_date" not in st.session_state:
    st.session_state.cal_selected_date = max(session_dates).strftime("%d.%m.%Y") if session_dates else None

cal_year = st.session_state.cal_year
cal_month = st.session_state.cal_month

# Bounds of available session data
if session_dates:
    min_session = min(session_dates)
    max_session = max(session_dates)
    at_min = (cal_year, cal_month) <= (min_session.year, min_session.month)
    at_max = (cal_year, cal_month) >= (max_session.year, max_session.month)
else:
    at_min = at_max = True

def matches(t, query):
    fields = " ".join(t.get(f) or "" for f in ["title", "subtitle", "topic"])
    return fuzz.partial_ratio(query.lower(), fields.lower()) >= 75

def top_sort_key(t):
    m = re.search(r'\d+', t["top_id"])
    return (t["date"], 0 if "Tagesordnungspunkt" in t["top_id"] else 1, int(m.group()) if m else 0)

def render_top_list(filtered, expand_top_key, expanded_by_default=True, expand_first=False):
    sorted_filtered = sorted(filtered, key=top_sort_key)
    first_top = True
    for session_date, group in groupby(sorted_filtered, key=lambda t: t["date"]):
        tops_in_session = list(group)
        n = len(tops_in_session)
        with st.expander(f"{session_date}  –  {n} Tagesordnungspunkte (TOP) und Zusatzpunkte (ZP)", expanded=expanded_by_default):
            for t in tops_in_session:
                nav_label = t["top_id"].replace("\xa0", " ").replace("Tagesordnungspunkt ", "TOP ").replace("Zusatzpunkt ", "ZP ")
                subs = t.get("subtopics") or []
                raw_topic = t.get("topic") or t.get("title") or t.get("subtitle") or ""
                if not raw_topic and subs:
                    first_title = subs[0].get("title", "").replace("\xa0", " ")
                    raw_topic = (first_title[:60] + " …") if len(first_title) > 60 else first_title
                topic = raw_topic or nav_label
                full_title = t.get("title") or t.get("subtitle", "")
                suffix = "" if t["active"] else "  *(Keine Parteireden)*"
                has_subtopics = bool(subs)
                if has_subtopics:
                    expander_label = f"{nav_label}  –  **Themenblock:** {topic}{suffix}"
                else:
                    expander_label = f"{nav_label}  –  {topic}{suffix}"
                is_back_target = t["top_key"] == expand_top_key
                open_this = is_back_target or (expand_first and first_top)
                first_top = False
                with st.expander(expander_label, expanded=open_this):
                    if full_title and full_title != topic:
                        st.caption(full_title)
                    if t["active"]:
                        page_obj = st.session_state.get("topic_pages", {}).get(t["top_key"])
                        if page_obj:
                            if st.button("Zusammenfassungen ansehen →", key=f"sum_{t['top_key']}"):
                                st.switch_page(page_obj)
                    else:
                        drs_subs = [s for s in subs if s.get("drucksache_url")]
                        top_drs_url = t.get("drucksache_url", "")
                        pdf_url = t.get("pdf_url", "")
                        if drs_subs:
                            st.markdown(
                                '<em style="color:#aaa; font-size:0.8rem">Keine Parteireden – Drucksachen:</em>',
                                unsafe_allow_html=True,
                            )
                            for s in drs_subs:
                                nas_clean = re.sub(r'^(?:\d+\s+)?[a-z]\)\s*', '', s.get("nas", "")).strip()
                                full = s.get("title") or nas_clean
                                label = (full[:80] + "…") if len(full) > 80 else full
                                st.markdown(
                                    f'<a href="{s["drucksache_url"]}" target="_blank" '
                                    f'style="color:#FB8500; font-size:0.85rem; text-decoration:none">'
                                    f'&#128203; {s["key"]}) {label}</a>',
                                    unsafe_allow_html=True,
                                )
                        elif top_drs_url:
                            st.markdown(
                                f'<a href="{top_drs_url}" target="_blank" '
                                f'style="color:#FB8500; font-size:0.85rem; text-decoration:none">'
                                f'&#128203; Drucksache öffnen</a>'
                                f'<em style="color:#aaa; font-size:0.8rem">&nbsp;– Keine Parteireden</em>',
                                unsafe_allow_html=True,
                            )
                        elif pdf_url:
                            escaped = nav_label.replace("'", "\\'")
                            st.markdown(
                                f'<a href="{pdf_url}" target="_blank" '
                                f'onclick="navigator.clipboard.writeText(\'{escaped}\')" '
                                f'style="color:#FB8500; font-size:0.85rem; text-decoration:none">&#128203; PDF öffnen</a>'
                                f'<em style="color:#aaa; font-size:0.8rem">&nbsp;– Keine Parteireden</em>',
                                unsafe_allow_html=True,
                            )
                        else:
                            st.caption("Keine Parteireden")

MONTHS_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni",
             "Juli", "August", "September", "Oktober", "November", "Dezember"]

search = st.text_input("🔍 Sitzungen durchsuchen", placeholder="z.B. Digitalsteuer, Mietrecht, Klimaschutz ...")
expand_top_key = st.session_state.get("expand_top_key", "")

# ── Search mode: full-width results across all data ───────────────────────────
if search:
    filtered = [t for t in all_topics if matches(t, search)]
    if not filtered:
        st.info("Keine Tagesordnungspunkte gefunden.")
    else:
        st.caption(f"{len(filtered)} Ergebnis{'se' if len(filtered) != 1 else ''} in allen Sitzungen")
        render_top_list(filtered, expand_top_key, expanded_by_default=False)

# ── Calendar mode ─────────────────────────────────────────────────────────────
else:
    cal_col, list_col = st.columns([1, 2], gap="large")

    with cal_col:
        prev_col, month_col, next_col = st.columns([1, 4, 1], gap="small")
        with prev_col:
            if st.button("‹", key="cal_prev", disabled=at_min):
                if cal_month == 1:
                    st.session_state.cal_year -= 1
                    st.session_state.cal_month = 12
                else:
                    st.session_state.cal_month -= 1
                st.session_state.cal_selected_date = None
                st.rerun()
        with month_col:
            st.markdown(
                f"<div style='text-align:center; font-weight:600; font-size:0.95rem; padding:4px 0'>"
                f"{MONTHS_DE[cal_month - 1]} {cal_year}</div>",
                unsafe_allow_html=True,
            )
        with next_col:
            if st.button("›", key="cal_next", disabled=at_max, use_container_width=True):
                if cal_month == 12:
                    st.session_state.cal_year += 1
                    st.session_state.cal_month = 1
                else:
                    st.session_state.cal_month += 1
                st.session_state.cal_selected_date = None
                st.rerun()

        hdr_cols = st.columns(7, gap="small")
        for i, d in enumerate(["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]):
            hdr_cols[i].markdown(
                f"<div style='text-align:center; font-size:0.7rem; color:#888; font-weight:600'>{d}</div>",
                unsafe_allow_html=True,
            )

        for week in cal_module.monthcalendar(cal_year, cal_month):
            week_cols = st.columns(7, gap="small")
            for i, day in enumerate(week):
                if day == 0:
                    week_cols[i].markdown(" ")
                    continue
                day_date = date(cal_year, cal_month, day)
                date_str = day_date.strftime("%d.%m.%Y")
                is_session = day_date in session_dates
                is_selected = st.session_state.cal_selected_date == date_str
                if is_session:
                    btn_type = "primary" if is_selected else "secondary"
                    if week_cols[i].button(str(day), key=f"cal_{date_str}", type=btn_type, use_container_width=True):
                        st.session_state.cal_selected_date = date_str
                        st.rerun()
                else:
                    week_cols[i].button(str(day), key=f"cal_{date_str}", disabled=True, use_container_width=True)

    with list_col:
        cal_selected = st.session_state.get("cal_selected_date")
        if not all_topics:
            st.info("Keine Tagesordnungspunkte verfügbar.")
        elif not cal_selected:
            st.info("Bitte wähle einen Tag im Kalender aus.")
        else:
            filtered = [t for t in all_topics if t["date"] == cal_selected]
            if not filtered:
                st.info("Keine Tagesordnungspunkte für diesen Tag.")
            else:
                is_first_visit = not st.session_state.get("visited")
                st.session_state.visited = True
                render_top_list(filtered, expand_top_key, expanded_by_default=True,
                                expand_first=is_first_visit and not expand_top_key)

if expand_top_key:
    st.session_state.expand_top_key = ""

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .faq-details summary { list-style: none; }
    .faq-details summary::-webkit-details-marker { display: none; }
    .faq-details summary::before { content: "▸ "; }
    .faq-details[open] summary::before { content: "▾ "; }
    .faq-details summary:hover { color: #555; text-decoration: underline; }
    </style>
    <details class="faq-details" style="color:#888; font-size:0.8rem; margin-top:1rem">
        <summary style="cursor:pointer; display:inline">
            Warum sind manche Nummern übersprungen?
        </summary>
        <p style="margin-top:0.5rem; line-height:1.6">
            Das ist normal und kein Fehler. Tagesordnungspunkte können kurzfristig verschoben, abgesetzt oder
            schriftlich zu Protokoll gegeben werden — die Nummer bleibt dann trotzdem vergeben. Manchmal kommen
            auch Zusatzpunkte (ZP) hinzu, die außerhalb der regulären Reihenfolge behandelt werden.
        </p>
    </details>
    """,
    unsafe_allow_html=True,
)

kw = st.session_state.get("kw_info")
earliest = st.session_state.get("earliest_date")
if kw or earliest:
    st.divider()
    if earliest and kw:
        st.caption(f"Datenstand: {earliest} – {kw}")
    elif kw:
        st.caption(f"Datenstand: {kw}")
    elif earliest:
        st.caption(f"Datenstand: {earliest}")
