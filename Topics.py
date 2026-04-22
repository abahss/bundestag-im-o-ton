import re
import requests
import streamlit as st
import streamlit.components.v1 as components


def parse_summary(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Returns (kernposition, [(quote_text, pdf_url), ...])"""
    kernposition = ""
    quotes = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("**Kernposition:**"):
            kernposition = line.replace("**Kernposition:**", "").strip()
        elif line.startswith('*"') or line.startswith('"'):
            id_match = re.search(r'\[(ID\w+)\]', line)
            quote_match = re.search(r'"(.+?)"', line)
            if quote_match:
                quote_text = quote_match.group(1)
                pdf_url = ""
                if id_match:
                    sid = id_match.group(1)
                    wp = sid[2:4]
                    session = sid[4:6].zfill(3)
                    pdf_url = f"https://dserver.bundestag.de/btp/{wp}/{wp}{session}.pdf"
                quotes.append((quote_text, pdf_url))
    return kernposition, quotes


TOOLTIP_CSS = """
<style>
.quelle-wrap { position: relative; display: inline-block; }
.quelle-wrap .tooltip {
    visibility: hidden; opacity: 0;
    background: #023047; color: #fff;
    font-size: 0.68rem; line-height: 1.4;
    border-radius: 6px; padding: 6px 10px;
    width: 210px;
    position: absolute; bottom: 130%; left: 50%; transform: translateX(-50%);
    transition: opacity 0.2s;
    z-index: 99; pointer-events: none;
}
.quelle-wrap:hover .tooltip { visibility: visible; opacity: 1; }
</style>
"""

TOOLTIP_TEXT = "Zitat wird kopiert und PDF öffnet sich – Zitat mit &#8984;+F / Strg+F im PDF suchen."


def quotes_html(quotes: list[tuple[str, str]]) -> str:
    if not quotes:
        return "<p style='color:#888; font-size:0.8rem'>Keine Zitate verfügbar.</p>"
    items = [TOOLTIP_CSS]
    for quote_text, pdf_url in quotes:
        escaped = quote_text.replace("\\", "\\\\").replace("'", "\\'")
        if pdf_url:
            link = (
                f'<span class="quelle-wrap">'
                f'<a href="{pdf_url}" target="_blank" '
                f'onclick="navigator.clipboard.writeText(\'{escaped}\')" '
                f'style="font-size:0.7rem; color:#FB8500; text-decoration:none; white-space:nowrap">&#128203; Quelle</a>'
                f'<span class="tooltip">{TOOLTIP_TEXT}</span>'
                f'</span>'
            )
        else:
            link = ""
        items.append(
            f'<div style="margin-bottom:10px; font-size:0.78rem; line-height:1.5; color:#023047">'
            f'<em>&#8222;{quote_text}&#8220;</em>&nbsp;{link}'
            f'</div>'
        )
    return "\n".join(items)


PARTIES = [
    ("LINKE", "Die Linke"),
    ("GRÜNEN", "B90 – Die Grünen"),
    ("SPD", "SPD"),
    ("CDUCSU", "CDU/CSU"),
    ("AFD", "AfD"),
]

PARTY_COLORS = {
    "AFD": "#009EE0",
    "GRÜNEN": "#46962B",
    "CDUCSU": "#000000",
    "LINKE": "#BE3075",
    "SPD": "#E3000F",
}


def render(top_key: str, title: str = "", subtitle: str = ""):
    if title:
        st.markdown(f"### {title}")
    if subtitle and subtitle != title:
        st.caption(subtitle)

    with st.spinner("Lade Zusammenfassungen...", show_time=True):
        try:
            data = requests.get(
                "http://localhost:8000/summaries",
                params={"top_key": top_key},
            ).json()
        except Exception as e:
            st.error(f"Fehler beim Laden: {e}")
            return

    for key, label in PARTIES:
        color = PARTY_COLORS.get(key, "#219EBC")
        raw = data.get(key, {}).get("summary", "")

        st.markdown(
            f"<div style='color:{color}; font-weight:bold; font-size:0.9rem; margin-top:0.4rem'>{label}</div>",
            unsafe_allow_html=True
        )

        if not raw:
            st.caption("Keine Daten für diesen Tagesordnungspunkt.")
            continue

        kernposition, quotes = parse_summary(raw)

        col_k, col_q = st.columns([2, 3], gap="medium")
        with col_k:
            st.container(border=True, height=200).markdown(
                f"<div style='font-size:0.85rem; line-height:1.6'>{kernposition or raw}</div>",
                unsafe_allow_html=True
            )
        with col_q:
            components.html(
                f"""
                <style>body {{ margin: 0; padding: 0; }}</style>
                <div style="
                    height: 198px; overflow-y: auto; padding: 8px 12px;
                    border: 1px solid #219EBC; border-radius: 8px;
                    background: #fff; box-sizing: border-box;
                ">
                    {quotes_html(quotes)}
                </div>
                """,
                height=200,
            )
