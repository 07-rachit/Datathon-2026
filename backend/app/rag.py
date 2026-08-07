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


import re

def build_index(db: Session):
    """Chunk all cases currently in DB and fit the TF-IDF matrix."""
    global _chunks, _vectorizer, _matrix, HAS_SKLEARN
    
    if not HAS_SKLEARN:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer as Vec
            from sklearn.metrics.pairwise import cosine_similarity as CosSim
            globals()['TfidfVectorizer'] = Vec
            globals()['cosine_similarity'] = CosSim
            globals()['HAS_SKLEARN'] = True
        except ImportError:
            pass

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
        fir_no = c.fir_details.crime_no if c.fir_details else ""
        overview_text = f"Case {c.case_id} ({c.title}): Category {c.crime_type}, Severity {c.severity}. Status {c.status}. Location {c.district}, {c.station_name}. FIR: {fir_no}. Summary: {c.summary or ''}"
        new_chunks.append(Chunk(f"{c.case_id}_overview", c.id, c.case_id, "overview", overview_text))

        people = []
        for p in c.persons or []:
            people.append(f"{p.role_in_case or 'Person'} {p.name} (Phone: {p.phone_number or 'N/A'}, MO: {p.mo_tags or ''})")
        for ev in c.evidence or []:
            people.append(f"Evidence: {ev.description or ''}")

        if people:
            people_text = f"Case {c.case_id} Entities & Evidence: " + "; ".join(people)
            new_chunks.append(Chunk(f"{c.case_id}_people", c.id, c.case_id, "people_evidence", people_text))

    if not new_chunks:
        return 0

    vec = None
    mat = None
    if HAS_SKLEARN and TfidfVectorizer is not None:
        try:
            vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
            mat = vec.fit_transform([ch.text for ch in new_chunks])
        except Exception as e:
            print(f"--> RAG TF-IDF build notice: {e}")

    with _lock:
        _chunks = new_chunks
        _vectorizer = vec
        _matrix = mat

    return len(new_chunks)


def get_case_chunks(identifier: str) -> List[Chunk]:
    """Return all chunks associated with a case by database ID or case code."""
    with _lock:
        return [c for c in _chunks if c.case_id == identifier or c.case_code == identifier]


def retrieve(query: str, top_k: int = 3) -> List[Tuple[Chunk, float]]:
    """Return top_k most relevant chunks for a user query as (Chunk, score) tuples."""
    with _lock:
        if not _chunks:
            return []

        raw_words = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 2]
        stop_words = {"tell", "about", "what", "where", "find", "show", "case", "cases", "with", "this", "that", "from"}
        keywords = [w for w in raw_words if w not in stop_words]

        if not HAS_SKLEARN or _vectorizer is None or _matrix is None:
            scored = []
            for ch in _chunks:
                text_lower = ch.text.lower()
                score = sum(1 for kw in keywords if kw in text_lower)
                if score > 0:
                    normalized_score = min(0.99, 0.4 + (score * 0.15))
                    scored.append((ch, normalized_score))
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]

        query_vec = _vectorizer.transform([query])
        scores = cosine_similarity(query_vec, _matrix)[0]

        ranked = sorted(zip(_chunks, scores), key=lambda x: x[1], reverse=True)
        results = [(chunk, float(score)) for chunk, score in ranked[:top_k] if score > 0.03]

        if not results and keywords:
            scored = []
            for ch in _chunks:
                text_lower = ch.text.lower()
                score = sum(1 for kw in keywords if kw in text_lower)
                if score > 0:
                    normalized_score = min(0.99, 0.4 + (score * 0.15))
                    scored.append((ch, normalized_score))
            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]

        return results


def get_case_chunks(case_id: str) -> List[Chunk]:
    """Return all chunks belonging to a given case_id or case_code."""
    with _lock:
        if not _chunks:
            return []
        return [c for c in _chunks if c.case_id == case_id or c.case_code == case_id]


def similar_to_case(case_id: str, top_k: int = 4):
    """Find other cases textually similar to a given case."""
    with _lock:
        if not _chunks:
            return []
        if not HAS_SKLEARN or _vectorizer is None or _matrix is None:
            return []
        own_chunks = [c for c in _chunks if (c.case_id == case_id or c.case_code == case_id) and c.section == "overview"]
        if not own_chunks:
            return []
        query_vec = _vectorizer.transform([own_chunks[0].text])
        scores = cosine_similarity(query_vec, _matrix)[0]
        ranked = sorted(zip(_chunks, scores), key=lambda x: x[1], reverse=True)
        seen_cases = {case_id}
        results = []
        for chunk, score in ranked:
            if chunk.case_id in seen_cases or chunk.case_code in seen_cases or chunk.section != "overview":
                continue
            seen_cases.add(chunk.case_id)
            seen_cases.add(chunk.case_code)
            results.append((chunk, float(score)))
            if len(results) >= top_k:
                break
        return results

