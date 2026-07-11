from practicepreach.constants import BUNDESTAG_WAHLPERIODE

def convert_to_wp_start(date):
    for wp, (start, end) in BUNDESTAG_WAHLPERIODE.items():
        if start <= date <= end:
            return start
    return None
