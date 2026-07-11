import matplotlib.pyplot as plt
from practicepreach.keyword_matching.keyword_cmp_matching import *


stopwords = import_stopwords()
rag = Rag()
keywords_dict = extract_keyword('Was sagt die Partei über Einkommensgerechtigkeit?',20,rag,'speech', stopwords)

cmp = find_keywords_with_cmp_codes(import_manifesto_cmp('LINKE',20), keywords_dict['LINKE'], 'LINKE')
data = most_frequent_cmp_with_counts(cmp)


def plot_dominant_cmp_per_keyword(data):
    keywords = list(data.keys())
    counts = [data[k]["count"] for k in keywords]
    cmp_codes = [data[k]["cmp_code"] for k in keywords]

    plt.figure(figsize=(10, 6))
    plt.barh(keywords, counts)
    plt.xlabel("Frequency of dominant cmp_code")
    plt.title("Dominant cmp_code per keyword")

    # annotate cmp_code on bars
    for i, cmp_code in enumerate(cmp_codes):
        plt.text(counts[i] + 0.1, i, cmp_code, va="center")

    plt.tight_layout()
    plt.show()

plot_dominant_cmp_per_keyword(data)
