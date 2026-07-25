"""
Lightweight RAG retrieval layer.

Uses TF-IDF + cosine similarity as the "vector search" step (no external
embedding downloads needed, so it runs anywhere). Swap `_vectorizer` /
`_matrix` for a real embedding model + vector DB (e.g. pgvector, Chroma,
Pinecone) later without changing the router code, since `retrieve()` is
the only function callers depend on.
"""
import threading
from dataclasses import dataclass
from typing import List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
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
_vectorizer: TfidfVectorizer | None = None
_matrix = None


def _case_to_chunks(case: models.Case) -> List[Chunk]:
    chunks = []

    fir = case.fir_details
    comp = case.complainant
    
    fir_text = ""
    if fir:
        fir_text = (
            f"Crime No: {fir.crime_no}. Category: {fir.category.name if fir.category else ''}. "
            f"Gravity: {fir.gravity.name if fir.gravity else ''}. "
            f"Crime Head: {fir.crime_head.name if fir.crime_head else ''}. "
            f"Sub Head: {fir.crime_sub_head.name if fir.crime_sub_head else ''}. "
        )

    act_sec_text = ""
    if case.act_sections:
        act_sec_text = "Acts and Sections: " + "; ".join(
            f"{a.act.name if a.act else ''} Section {a.section.section_number if a.section else ''}"
            for a in case.act_sections
        )

    overview = (
        f"Case {case.case_id}: {case.title}. "
        f"Crime type: {case.crime_type}. District: {case.district}. "
        f"Station: {case.station_name}. Status: {case.status.value}. "
        f"Severity: {case.severity.value}. "
        f"Incident date: {case.incident_date.strftime('%d %b %Y')}. "
        f"{fir_text} {act_sec_text} "
        f"Summary: {case.summary or 'No summary recorded.'}"
    )
    chunks.append(Chunk(f"{case.id}-overview", case.id, case.case_id, "overview", overview))

    people_bits = [
        f"{p.name} ({p.role_in_case or 'unspecified role'}, phone {p.phone_number or 'unknown'})"
        for p in case.persons
    ]
    if comp:
        people_bits.append(f"Complainant: {comp.name}")

    evidence_bits = [f"{e.description}" for e in case.evidence]
    if people_bits or evidence_bits:
        text = f"Case {case.case_id} people and evidence. "
        if people_bits:
            text += "Persons of interest: " + "; ".join(people_bits) + ". "
        if evidence_bits:
            text += "Evidence collected: " + "; ".join(evidence_bits) + "."
        chunks.append(Chunk(f"{case.id}-people_evidence", case.id, case.case_id, "people_evidence", text))

    return chunks


def build_index(db: Session) -> int:
    """Rebuild the in-memory TF-IDF index from all cases in the DB."""
    global _chunks, _vectorizer, _matrix

    cases = (
        db.query(models.Case)
        .options(
            joinedload(models.Case.persons),
            joinedload(models.Case.evidence),
            joinedload(models.Case.fir_details),
            joinedload(models.Case.complainant),
            joinedload(models.Case.act_sections),
        )
        .all()
    )

    new_chunks: List[Chunk] = []
    for case in cases:
        new_chunks.extend(_case_to_chunks(case))

    with _lock:
        _chunks = new_chunks
        if _chunks:
            _vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                token_pattern=r"(?u)\b\w+\b",
                max_features=10000,
            )
            _matrix = _vectorizer.fit_transform([c.text for c in _chunks])
        else:
            _vectorizer = None
            _matrix = None

    return len(_chunks)


def retrieve(query: str, top_k: int = 5) -> List[Tuple[Chunk, float]]:
    """Return the top_k most relevant chunks for a natural-language query."""
    with _lock:
        if not _chunks or _vectorizer is None or _matrix is None:
            return []
        try:
            query_vec = _vectorizer.transform([query])
            scores = cosine_similarity(query_vec, _matrix)[0]
            ranked = sorted(zip(_chunks, scores), key=lambda x: x[1], reverse=True)
            results = [(chunk, float(score)) for chunk, score in ranked if score > 0.0]
            return results[:top_k]
        except Exception:
            return []


def get_case_chunks(case_id: str):
    """Return all indexed chunks belonging to one case (used for direct case-ID lookups)."""
    with _lock:
        return [c for c in _chunks if c.case_id == case_id]


def similar_to_case(case_id: str, top_k: int = 4):
    """Find other cases textually similar to a given case (for the 'Similar Cases' panel)."""
    with _lock:
        if not _chunks or _vectorizer is None or _matrix is None:
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
