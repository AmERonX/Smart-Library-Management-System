import os
from typing import Iterable, List, Tuple

import faiss
import numpy as np
import portalocker

from config import (
    FAISS_INDEX_DIR,
    FAISS_IDENTITY_INDEX_PATH,
    FAISS_TOPICAL_INDEX_PATH,
    FAISS_IDENTITY_LOCK_PATH,
    FAISS_TOPICAL_LOCK_PATH,
)
from config import EMBED_DIM as _DIM


def _ensure_dirs() -> None:
    os.makedirs(FAISS_INDEX_DIR, exist_ok=True)


def _paths(vector_type: str) -> Tuple[str, str]:
    if vector_type == "identity":
        return FAISS_IDENTITY_INDEX_PATH, FAISS_IDENTITY_LOCK_PATH
    if vector_type == "topical":
        return FAISS_TOPICAL_INDEX_PATH, FAISS_TOPICAL_LOCK_PATH
    raise ValueError("vector_type must be 'identity' or 'topical'")


def _normalize(v: np.ndarray) -> np.ndarray:
    v = v.astype(np.float32)
    n = np.linalg.norm(v)
    if n == 0:
        return v
    return v / n


def _load_or_create(index_path: str) -> faiss.IndexIDMap:
    if os.path.exists(index_path):
        idx = faiss.read_index(index_path)
        if not isinstance(idx, faiss.IndexIDMap):
            idx = faiss.IndexIDMap(idx)
        return idx
    base = faiss.IndexFlatIP(_DIM)
    return faiss.IndexIDMap(base)


def append(vector_type: str, faiss_id: int, vector: np.ndarray) -> None:
    _ensure_dirs()
    index_path, lock_path = _paths(vector_type)
    v = _normalize(vector)
    if v.shape[0] != _DIM:
        raise ValueError(f"Vector dim {v.shape[0]} != expected {_DIM}")

    with portalocker.Lock(lock_path, "a+b", timeout=30):
        index = _load_or_create(index_path)
        try:
            remove_ids = np.array([faiss_id], dtype=np.int64)
            index.remove_ids(remove_ids)
        except Exception:
            pass
        mat = np.expand_dims(v, axis=0).astype(np.float32)
        ids = np.array([faiss_id], dtype=np.int64)
        index.add_with_ids(mat, ids)
        faiss.write_index(index, index_path)


def rebuild(vector_type: str, rows: Iterable[Tuple[int, np.ndarray]]) -> None:
    _ensure_dirs()
    index_path, lock_path = _paths(vector_type)
    ids: List[int] = []
    vecs: List[np.ndarray] = []
    for fid, vec in rows:
        ids.append(int(fid))
        vecs.append(_normalize(vec))
    with portalocker.Lock(lock_path, "a+b", timeout=30):
        if not ids:
            idx = faiss.IndexIDMap(faiss.IndexFlatIP(_DIM))
            faiss.write_index(idx, index_path)
            return
        mat = np.vstack(vecs).astype(np.float32)
        idarr = np.array(ids, dtype=np.int64)
        idx = faiss.IndexIDMap(faiss.IndexFlatIP(_DIM))
        idx.add_with_ids(mat, idarr)
        faiss.write_index(idx, index_path)


def search(vector_type: str, query_vec: np.ndarray, k: int = 5) -> List[Tuple[int, float]]:
    index_path, _ = _paths(vector_type)
    if not os.path.exists(index_path):
        return []
    idx = faiss.read_index(index_path)
    q = _normalize(query_vec).astype(np.float32)
    D, I = idx.search(np.expand_dims(q, 0), k)
    ids = I[0].tolist()
    scores = D[0].tolist()
    return [(int(i), float(s)) for i, s in zip(ids, scores) if i != -1]
