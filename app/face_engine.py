import os
import base64
import threading
import cv2
import numpy as np
from scipy.spatial.distance import cosine
from app.config import CONFIDENCE_THRESHOLD, ANTI_SPOOFING, UPLOAD_DIR

_face_analyzer = None
RETRY_MODELS = False

_embedding_cache: list[tuple[int, str, np.ndarray]] = []
_cache_lock = threading.Lock()
_cache_dirty = True


def get_analyzer():
    global _face_analyzer, RETRY_MODELS
    if _face_analyzer is None and not RETRY_MODELS:
        try:
            import insightface
            from insightface.app import FaceAnalysis
            _face_analyzer = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
            _face_analyzer.prepare(ctx_id=0, det_thresh=0.5, det_size=(640, 640))
        except Exception as e:
            RETRY_MODELS = True
            raise RuntimeError(f"Error cargando insightface: {e}")
    return _face_analyzer


def _decode_image(image_data: str | bytes | np.ndarray) -> np.ndarray:
    if isinstance(image_data, np.ndarray):
        return image_data
    if isinstance(image_data, bytes):
        if len(image_data) < 100:
            raise ValueError("Imagen demasiado pequeña o vacía")
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("No se pudo decodificar la imagen (formato inválido)")
        return img
    if isinstance(image_data, str):
        if image_data.startswith("data:image"):
            image_data = image_data.split(",")[1]
        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("No se pudo decodificar la imagen (formato inválido)")
        return img
    raise ValueError("Unsupported image format")


def _check_liveness(img: np.ndarray) -> bool:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 20:
        return False
    return True


def detect_face(image_data: str | bytes | np.ndarray) -> dict:
    try:
        img = _decode_image(image_data)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    try:
        analyzer = get_analyzer()
        faces = analyzer.get(img)
        if not faces:
            return {"success": False, "error": "No se detectó ningún rostro"}
        face = faces[0]
        bbox = face.bbox.astype(int).tolist()
        return {
            "success": True,
            "bbox": bbox,
            "det_score": float(face.det_score),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def extract_embedding(image_data: str | bytes | np.ndarray) -> dict:
    try:
        img = _decode_image(image_data)
    except ValueError as e:
        return {"success": False, "error": str(e)}
    if ANTI_SPOOFING and not _check_liveness(img):
        return {"success": False, "error": "Posible foto o pantalla (laplaciano muy bajo)"}
    try:
        analyzer = get_analyzer()
        faces = analyzer.get(img)
        if not faces:
            return {"success": False, "error": "No se detectó ningún rostro"}
        face = faces[0]
        embedding = face.normed_embedding
        bbox = face.bbox.astype(int).tolist()
        return {
            "success": True,
            "embedding": embedding,
            "det_score": float(face.det_score),
            "bbox": bbox,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def compare_embeddings(embedding: np.ndarray, stored_embeddings: list[tuple[int, str, np.ndarray]]) -> dict | None:
    best_match = None
    best_distance = float("inf")
    for user_id, name, stored_emb in stored_embeddings:
        dist = cosine(embedding, stored_emb)
        if dist < best_distance:
            best_distance = dist
            best_match = (user_id, name, dist)
    if best_match and (1.0 - best_distance) >= CONFIDENCE_THRESHOLD:
        return {
            "user_id": best_match[0],
            "user_name": best_match[1],
            "confidence": float(1.0 - best_distance),
            "distance": float(best_distance),
        }
    return None


def embedding_to_str(embedding: np.ndarray) -> str:
    return base64.b64encode(embedding.astype(np.float32).tobytes()).decode()


def str_to_embedding(embedding_str: str) -> np.ndarray:
    raw = base64.b64decode(embedding_str)
    return np.frombuffer(raw, dtype=np.float32)


def register_face(image_data: str | bytes | np.ndarray) -> dict:
    result = extract_embedding(image_data)
    if not result["success"]:
        return result
    return {
        "success": True,
        "embedding": result["embedding"],
        "embedding_str": embedding_to_str(result["embedding"]),
    }


def invalidate_cache():
    global _cache_dirty
    with _cache_lock:
        _cache_dirty = True


def get_cached_embeddings(users: list) -> list[tuple[int, str, np.ndarray]]:
    global _cache_dirty, _embedding_cache
    with _cache_lock:
        if not _cache_dirty and _embedding_cache:
            return _embedding_cache
        _embedding_cache = [(u.id, u.name, str_to_embedding(u.embedding)) for u in users if u.active]
        _cache_dirty = False
        return _embedding_cache
