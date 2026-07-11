from datetime import date

BUNDESTAG_WAHLPERIODE = {
    1:  (date(1949, 9, 7),  date(1953, 10, 6)),
    2:  (date(1953, 10, 6), date(1957, 10, 15)),
    3:  (date(1957, 10, 15), date(1961, 10, 17)),
    4:  (date(1961, 10, 17), date(1965, 10, 19)),
    5:  (date(1965, 10, 19), date(1969, 10, 20)),
    6:  (date(1969, 10, 20), date(1972, 12, 13)),
    7:  (date(1972, 12, 13), date(1976, 12, 13)),
    8:  (date(1976, 12, 13), date(1980, 11, 4)),
    9:  (date(1980, 11, 4), date(1983, 3, 29)),
    10: (date(1983, 3, 29), date(1987, 2, 18)),
    11: (date(1987, 2, 18), date(1990, 12, 20)),
    12: (date(1990, 12, 20), date(1994, 11, 10)),
    13: (date(1994, 11, 10), date(1998, 10, 26)),
    14: (date(1998, 10, 26), date(2002, 10, 17)),
    15: (date(2002, 10, 17), date(2005, 10, 18)),
    16: (date(2005, 10, 18), date(2009, 10, 27)),
    17: (date(2009, 10, 27), date(2013, 10, 22)),
    18: (date(2013, 10, 22), date(2017, 10, 24)),
    19: (date(2017, 10, 24), date(2021, 10, 26)),
    20: (date(2021, 10, 26), date(2025, 3, 22)),
    21: (date(2025, 3, 23), date.today())  # still ongoing, would need to be updated in the next Wahlperiode
}

# https://www.notion.so/ChatGPT-generated-Topic-based-on-all-Manifestos-from-2025-2bc01f2a08b980ffa6e5c00e92d9f24b
POLITICAL_TOPICS = {
    "economy": "Wirtschaft & Wachstum",
    "social": "Soziale Sicherheit & Wohlfahrt",
    "work": "Arbeit & Arbeitsmarkt",
    "education": "Bildung",
    "environment": "Klima, Umwelt & Energie",
    "migration": "Migration, Integration & Staatsangehörigkeit",
    "housing": "Wohnen & Stadtentwicklung",
    "technology": "Digitalisierung & Technologische Innovation",
    "security": "Innere Sicherheit, Recht & Ordnung",
    "foreign_policy": "Außenpolitik, Sicherheit & Europa",
}

PARTIES_LIST_OLD = ["AfD", "SPD", "CDU/CSU", "BÜNDNIS 90/DIE GRÜNEN", "Die Linke"]
PARTIES_LIST = ["AFD", "SPD", "CDUCSU", "GRÜNEN", "LINKE"]

NOT_ENOUGHT_DATA_FOR_SCORE = "Not enought data"

PARTY_CODE = {
    "AFD": "41953",
    "SPD": "41320",
    "CDUCSU": "41310",
    "GRÜNEN": "41221",
    "LINKE": "41223",
}
