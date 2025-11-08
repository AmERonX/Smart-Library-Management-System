import numpy as np
import google.generativeai as genai
from typing import Optional
from config import GOOGLE_API_KEY

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

EMBED_DIM = 768


def embed_text(text: str) -> np.ndarray:
    if not GOOGLE_API_KEY:
        raise RuntimeError("Embedding service not configured: GOOGLE_API_KEY is missing")
    resp = genai.embed_content(model="models/text-embedding-004", content=text)
    v = np.array(resp["embedding"], dtype=np.float32)
    n = float(np.linalg.norm(v))
    return v / n if n else v
