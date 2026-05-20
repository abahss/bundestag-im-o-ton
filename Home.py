import calendar as cal_module
import re
import requests
import streamlit as st
from datetime import date, datetime
from itertools import groupby

st.set_page_config(
    page_title="Practice What You Preach",
    page_icon="🦔",
    layout='wide'
)

st.markdown("""
<style>
header.stAppHeader { background-color: transparent; }
section.stMain .block-container { padding-top: 0rem; z-index: 1; }
[data-testid="stPageLink"] p { white-space: normal !important; word-break: break-word; }
/* Calendar day buttons: compact, square-ish */
div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] button {
    padding: 2px 4px !important;
    min-height: 0 !important;
    font-size: 0.8rem !important;
}
</style>""", unsafe_allow_html=True)

st.write("<h1 style='text-align: center;'>Practice What You Preach</h1>", unsafe_allow_html=True)
st.write(
    "Was sagen die Parteien wirklich im Bundestag – und wie klingt das im Vergleich zu ihren Wahlversprechen?"
)
st.write(
    "Für jeden Tagesordnungspunkt einer Sitzung fasst die App zusammen, welche Position jede Partei vertreten hat. "
    "Direkte Zitate aus dem Plenarprotokoll belegen die Zusammenfassungen und lassen sich mit einem Klick im Original-PDF nachschlagen."
)
st.write(
    "Unten findest du das Inhaltsverzeichnis der verfügbaren Sitzungen. "
    "Punkte ohne Parteireden – etwa wenn nur Minister gesprochen haben – sind ausgegraut und verlinken direkt auf das Protokoll."
)

try:
    all_topics = requests.get("http://localhost:8000/all_topics").json()
except Exception:
    all_topics = []

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
    st.session_state.cal_selected_date = None

cal_year = st.session_state.cal_year
cal_month = st.session_state.cal_month

search = st.text_input("🔍 Tagesordnungspunkte durchsuchen", placeholder="z.B. Digitalsteuer, Mietrecht, Klimaschutz ...")

def matches(t, query):
    q = query.lower()
    return any(q in (t.get(f) or "").lower() for f in ["title", "subtitle", "top_id"])

def top_sort_key(t):
    m = re.search(r'\d+', t["top_id"])
    return (t["date"], 0 if "Tagesordnungspunkt" in t["top_id"] else 1, int(m.group()) if m else 0)

MONTHS_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni",
             "Juli", "August", "September", "Oktober", "November", "Dezember"]

# ── Main layout ──────────────────────────────────────────────────────────────
cal_col, list_col = st.columns([1, 2], gap="large")

# ── Calendar ─────────────────────────────────────────────────────────────────
with cal_col:
    # Month navigation
    prev_col, month_col, next_col = st.columns([1, 4, 1])
    with prev_col:
        if st.button("‹", key="cal_prev"):
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
        if st.button("›", key="cal_next"):
            if cal_month == 12:
                st.session_state.cal_year += 1
                st.session_state.cal_month = 1
            else:
                st.session_state.cal_month += 1
            st.session_state.cal_selected_date = None
            st.rerun()

    # Weekday headers
    hdr_cols = st.columns(7, gap="small")
    for i, d in enumerate(["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]):
        hdr_cols[i].markdown(
            f"<div style='text-align:center; font-size:0.7rem; color:#888; font-weight:600'>{d}</div>",
            unsafe_allow_html=True,
        )

    # Day grid
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
                if week_cols[i].button(str(day), key=f"cal_{date_str}", type=btn_type):
                    # Toggle selection
                    st.session_state.cal_selected_date = None if is_selected else date_str
                    st.rerun()
            else:
                week_cols[i].markdown(
                    f"<div style='text-align:center; color:#ccc; font-size:0.82rem; padding:3px 0'>{day}</div>",
                    unsafe_allow_html=True,
                )

# ── Session list ──────────────────────────────────────────────────────────────
with list_col:
    # Filter to current month, then by search
    month_topics = [
        t for t in all_topics
        if datetime.strptime(t["date"], "%d.%m.%Y").month == cal_month
        and datetime.strptime(t["date"], "%d.%m.%Y").year == cal_year
    ]
    filtered = [t for t in month_topics if not search or matches(t, search)]

    if not all_topics:
        st.info("Keine Tagesordnungspunkte verfügbar.")
    elif not month_topics:
        st.info(f"Keine Sitzungen im {MONTHS_DE[cal_month - 1]} {cal_year}.")
    elif not filtered:
        st.info("Keine Tagesordnungspunkte gefunden.")
    else:
        sorted_filtered = sorted(filtered, key=top_sort_key)
        for session_date, group in groupby(sorted_filtered, key=lambda t: t["date"]):
            tops_in_session = list(group)
            n = len(tops_in_session)
            is_selected_session = st.session_state.cal_selected_date == session_date

            with st.expander(
                f"{session_date}  –  {n} Tagesordnungspunkte",
                expanded=is_selected_session or bool(search),
            ):
                for t in tops_in_session:
                    nav_label = t["top_id"].replace("\xa0", " ").replace("Tagesordnungspunkt ", "TOP ").replace("Zusatzpunkt ", "ZP ")
                    topic = t.get("topic") or nav_label
                    full_title = t.get("title") or t.get("subtitle", "")

                    suffix = "" if t["active"] else "  *(Keine Parteireden)*"
                    with st.expander(f"{nav_label}  –  {topic}{suffix}"):
                        if full_title and full_title != topic:
                            st.caption(full_title)

                        if t["active"]:
                            page_obj = st.session_state.get("topic_pages", {}).get(t["top_key"])
                            if page_obj:
                                st.page_link(page_obj, label="→ Zusammenfassungen ansehen")
                        else:
                            drs_subs = [s for s in (t.get("subtopics") or []) if s.get("drucksache_url")]
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
    info_parts = []
    if earliest:
        info_parts.append(f"Älteste Sitzung: {earliest}")
    if kw:
        info_parts.append(f"Neueste Daten: {kw}")
    st.caption("  ·  ".join(info_parts))
