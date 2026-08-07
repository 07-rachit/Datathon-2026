"""
Lightweight RAG retrieval layer.

Uses TF-IDF + cosine similarity as the "vector search" step.
Falls back safely to keyword search if sklearn is unavailable.
"""
import threading
from dataclasses import dataclass
from typing import List, Tuple

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    TfidfVectorizer = None
    cosine_similarity = None

from sqlalchemy.orm import Session, joinedload
from app import models


@dataclass
class Chunk:
    chunk_id: str
    case_id: str
    case_code: str
    section: str  # "overview" | "people_evidence"
    text: str


_lock = threading.Lock()
_chunks: List[Chunk] = []
_vectorizer = None
_matrix = None


def build_index(db: Session):
    """Chunk all cases currently in DB and fit the TF-IDF matrix."""
    global _chunks, _vectorizer, _matrix
    if not HAS_SKLEARN:
        print("--> RAG notice: scikit-learn unavailable, using keyword retrieval fallback.")
        return

    cases = (
        db.query(models.Case)
        .options(
            joinedload(models.Case.fir_details),
            joinedload(models.Case.persons),
            joinedload(models.Case.evidence),
        )
        .all()
    )

    new_chunks: List[Chunk] = []
    for c in cases:
        fir_no = c.fir_details.crime_no if getattr(c, "fir_details", None) else ""
        overview_text = (
            f"Case {c.case_id} ({c.title}): Crime {c.crime_type}, Severity {c.severity}. "
            f"Status {c.status}. District {c.district}, Station {c.station_name}. "
            f"FIR: {fir_no}. Summary: {c.summary or ''}"
        )
        new_chunks.append(Chunk(f"{c.case_id}_overview", c.case_id, c.case_id, "overview", overview_text))

        entities = []
        for p in getattr(c, "persons", []) or []:
            role = p.role_in_case or "person"
            entities.append(f"{role.capitalize()} {p.name} (notes: {p.notes or ''}, mo: {p.mo_tags or ''})")
        for ev in getattr(c, "evidence", []) or []:
            entities.append(f"Evidence {ev.item_type}: {ev.description or ''}")

        if entities:
            entities_text = f"Case {c.case_id} Entities & Evidence: " + "; ".join(entities)
            new_chunks.append(Chunk(f"{c.case_id}_entities", c.case_id, c.case_id, "people_evidence", entities_text))

    if not new_chunks:
        return

    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    mat = vec.fit_transform([ch.text for ch in new_chunks])

    with _lock:
        _chunks = new_chunks
        _vectorizer = vec
        _matrix = mat

    return len(new_chunks)


def retrieve(query: str, top_k: int = 3) -> List[Chunk]:
    """Return top_k most relevant chunks for a user query."""
    with _lock:
        if not _chunks:
            return []
        if not HAS_SKLEARN or _vectorizer is None or _matrix is None:
            # Fallback simple keyword match
            keywords = [k.lower() for k in query.split() if len(k) > 2]
            scored = []
            for ch in _chunks:
                score = sum(1 for kw in keywords if kw in ch.text.lower())
                if score > 0:
                    scored.append((ch, float(score)))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [ch for ch, _ in scored[:top_k]]

        query_vec = _vectorizer.transform([query])
        scores = cosine_similarity(query_vec, _matrix)[0]

        ranked = sorted(zip(_chunks, scores), key=lambda x: x[1], reverse=True)
        return [chunk for chunk, score in ranked[:top_k] if score > 0.05]


def similar_to_case(case_id: str, top_k: int = 4):
    """Find other cases textually similar to a given case."""
    with _lock:
        if not _chunks:
            return []
        if not HAS_SKLEARN or _vectorizer is None or _matrix is None:
            return []
        own_chunks = [c for c in _chunks if c.case_id == case_id and c.section == "overview"]
        if not own_chunks:
            return []
        query_vec = _vectorizer.transform([own_chunks[0].text])
        scores = cosine_similarity(query_vec, _matrix)[0]
        ranked = sorted(zip(_chunks, scores), key=lambda x: x[1], reverse=True)
        seen_cases = {case_id}
        results = []
        for chunk, score in ranked:
            if chunk.case_id in seen_cases or chunk.section != "overview":
                continue
            seen_cases.add(chunk.case_id)
            results.append((chunk, float(score)))
            if len(results) >= top_k:
                break
        return results
