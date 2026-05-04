import requests
import streamlit as st

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

st.divider()

with st.expander("Warum sind manche Nummern übersprungen?"):
    st.write(
        "Das ist normal und kein Fehler. Tagesordnungspunkte können kurzfristig verschoben, abgesetzt oder "
        "schriftlich zu Protokoll gegeben werden — die Nummer bleibt dann trotzdem vergeben. Manchmal kommen "
        "auch Zusatzpunkte (ZP) hinzu, die außerhalb der regulären Reihenfolge behandelt werden."
    )

try:
    all_topics = requests.get("http://localhost:8000/all_topics").json()
except Exception:
    all_topics = []

search = st.text_input("🔍 Tagesordnungspunkte durchsuchen", placeholder="z.B. Digitalsteuer, Mietrecht, Klimaschutz ...")

def matches(t, query):
    q = query.lower()
    return any(q in (t.get(f) or "").lower() for f in ["title", "subtitle", "top_id"])

filtered = [t for t in all_topics if not search or matches(t, search)]

if not all_topics:
    st.info("Keine Tagesordnungspunkte verfügbar.")
elif not filtered:
    st.info("Keine Tagesordnungspunkte gefunden.")
else:
    from itertools import groupby
    import re
    def top_sort_key(t):
        m = re.search(r'\d+', t["top_id"])
        return (t["date"], 0 if "Tagesordnungspunkt" in t["top_id"] else 1, int(m.group()) if m else 0)
    sorted_filtered = sorted(filtered, key=top_sort_key)
    for session_date, group in groupby(sorted_filtered, key=lambda t: t["date"]):
        tops_in_session = list(group)
        n = len(tops_in_session)

        # Level 1: Datum – Anzahl TOPs
        with st.expander(f"{session_date}  –  {n} Tagesordnungspunkte", expanded=bool(search)):
            for t in tops_in_session:
                nav_label = t["top_id"].replace("Tagesordnungspunkt ", "TOP ").replace("Zusatzpunkt ", "ZP ")
                topic = t.get("topic") or nav_label
                full_title = t.get("title") or t.get("subtitle", "")

                # Level 2: TOP-Nummer – Topic (+ Hinweis wenn keine Parteireden)
                suffix = "" if t["active"] else "  *(Keine Parteireden)*"
                with st.expander(f"{nav_label}  –  {topic}{suffix}"):
                    # Level 3: Voller Titel
                    if full_title and full_title != topic:
                        st.caption(full_title)

                    if t["active"]:
                        page_obj = st.session_state.get("topic_pages", {}).get(t["top_key"])
                        if page_obj:
                            st.page_link(page_obj, label="→ Zusammenfassungen ansehen")
                    else:
                        pdf_url = t.get("pdf_url", "")
                        if pdf_url:
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
