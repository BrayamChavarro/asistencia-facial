from fastapi import APIRouter, UploadFile, File, HTTPException
from app.face_engine import detect_face

router = APIRouter(prefix="/api/face", tags=["face"])


@router.post("/detect")
async def detect(image: UploadFile = File(...)):
    img_bytes = await image.read()
    result = detect_face(img_bytes)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
