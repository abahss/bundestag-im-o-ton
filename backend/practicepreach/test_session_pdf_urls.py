from practicepreach.tools import session_pdf_urls_from_metadatas


def test_two_digit_session():
    meta = [{"id": "ID219900200", "top_key": "99_Tagesordnungspunkt 7"}]
    assert session_pdf_urls_from_metadatas(meta) == {
        "99": "https://dserver.bundestag.de/btp/21/21099.pdf"
    }


def test_three_digit_session_regression():
    # Sitzung 100: Rede-IDs haben eine Ziffer mehr; früher wurde "10" abgeschnitten.
    meta = [{"id": "ID2110000100", "top_key": "100_Tagesordnungspunkt 35"}]
    assert session_pdf_urls_from_metadatas(meta) == {
        "100": "https://dserver.bundestag.de/btp/21/21100.pdf"
    }


def test_ignores_metadata_without_id_or_top_key():
    assert session_pdf_urls_from_metadatas([{}, {"id": "ID219900200"}]) == {}
