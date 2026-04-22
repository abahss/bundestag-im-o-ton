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
</style>""", unsafe_allow_html=True)

st.write("<h1 style='text-align: center;'>Practice What You Preach</h1>", unsafe_allow_html=True)
st.write(
    "Practice What You Preach zeigt, was Parteien im Bundestag wirklich sagen – und ob das mit ihrem Wahlprogramm übereinstimmt."
)
st.write("Halten die Parteien, was sie versprechen?")

kw = st.session_state.get("kw_info")
if kw:
    st.caption(f"Aktuelle Daten: {kw}")

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

if not all_topics:
    st.info("Keine Tagesordnungspunkte verfügbar.")
else:
    # Group by session date
    from itertools import groupby
    for session_date, group in groupby(all_topics, key=lambda t: t["date"]):
        st.markdown(f"**Sitzung vom {session_date}**")
        for t in group:
            top_id = t["top_id"]
            nav_label = top_id.replace("Tagesordnungspunkt ", "TOP ").replace("Zusatzpunkt ", "ZP ")
            title = t.get("title", "")
            subtitle = t.get("subtitle", "")
            parts = [p for p in [nav_label, title] if p]
            display = " – ".join(dict.fromkeys(parts))

            if t["active"]:
                page_obj = st.session_state.get("topic_pages", {}).get(t["top_key"])
                if page_obj:
                    st.page_link(page_obj, label=display)
            else:
                pdf_url = t.get("pdf_url", "")
                top_id_label = t["top_id"].replace("Tagesordnungspunkt ", "TOP ").replace("Zusatzpunkt ", "ZP ")
                if pdf_url:
                    escaped = top_id_label.replace("'", "\\'")
                    pdf_link = (
                        f'<a href="{pdf_url}" target="_blank" '
                        f'onclick="navigator.clipboard.writeText(\'{escaped}\')" '
                        f'style="color:#FB8500; font-size:0.75rem; text-decoration:none">&#128203; PDF</a>'
                    )
                else:
                    pdf_link = ""
                st.markdown(
                    f"<span style='color:#aaa; font-size:0.9rem'>⬜ {display}"
                    f"&nbsp;<em style='font-size:0.75rem'>Keine Parteireden</em>"
                    f"&nbsp;{pdf_link}</span>",
                    unsafe_allow_html=True,
                )
        st.markdown("")
