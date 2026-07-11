import numpy as np

def get_centroid_from_store(vector_store, docs_with_scores):
    # docs_with_scores: [(Document, score), ...]
    ids = [doc.id for doc, _ in docs_with_scores]

    # Use underlying Chroma collection
    res = vector_store._collection.get(ids=ids, include=["embeddings"])
    embs = np.array(res["embeddings"])
    return embs.mean(axis=0)

def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def content_alignment_from_store(vector_store, speech_docs, manifesto_docs):
    c_speech = get_centroid_from_store(vector_store, speech_docs)
    c_mani   = get_centroid_from_store(vector_store, manifesto_docs)

    return cosine(c_speech, c_mani)




# ≈ 1.0 → the content of speech and manifesto chunks retrieved by this query is very similar

# ≈ 0.5 → somewhat related but with different emphasis

# ≈ 0.0 → they react to the query with very different content
