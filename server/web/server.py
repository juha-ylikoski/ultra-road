from typing import Annotated
from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    Header,
)
from PIL import Image
from fastapi.responses import JSONResponse
import uvicorn
import io
from sqlalchemy.orm import Session
import sqlalchemy

from .annotate import slipsum
from . import db, models
from .db import get_db
from . import schemas


app = FastAPI(lifespan=db.lifespan)


@app.get("/")
async def index():
    return "foo"


@app.get("/kinds")
async def kinds(db: Session = Depends(get_db)) -> list[schemas.Kind]:
    return models.get_kinds(db)


@app.post("/kind")
async def new_kind(kind: schemas.Kind, db: Session = Depends(get_db)) -> int:
    return models.create_kind(db, kind)


@app.post("/post")
async def upload_image(
    x_latitude: Annotated[float, Header()],
    x_longitude: Annotated[float, Header()],
    x_text: Annotated[str, Header()],
    x_kind: Annotated[str, Header()],
    x_title: Annotated[str, Header()],
    x_address: Annotated[str, Header()],
    file: UploadFile = File(content_type="image/jpeg"),
    db: Session = Depends(get_db),
) -> int:
    image = await file.read()
    if x_kind not in [x.name for x in models.get_kinds(db)]:
        raise HTTPException(status_code=400, detail="Kind not allowed!")
    return models.create_post(
        db, x_latitude, x_longitude, x_text, image, x_kind, x_title, x_address
    )


@app.get("/posts")
async def get_posts(
    db: Session = Depends(get_db),
) -> list[schemas.BasePost]:
    return models.get_posts(db)


@app.get("/posts/{id}/img")
async def get_img(
    id: str,
    db: Session = Depends(get_db),
) -> bytes:
    img = models.get_post_img(db, id)
    return Response(content=img, media_type="img/jpeg")


@app.post("/posts/{id}/upvote")
async def upvote(
    id: str,
    db: Session = Depends(get_db),
) -> bytes:
    models.upvote(db, id)


@app.post("/annotate")
async def annotate_image(
    file: UploadFile = File(content_type="image/jpeg"),
) -> str:
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))
    return slipsum()


@app.exception_handler(sqlalchemy.exc.IntegrityError)
def unique_violation(request: Request, exc: sqlalchemy.exc.IntegrityError):
    return JSONResponse(status_code=400, content={"message": "Already exists!"})


@app.exception_handler(sqlalchemy.exc.NoResultFound)
def not_found(request: Request, exc: sqlalchemy.exc.NoResultFound):
    return JSONResponse(status_code=404, content={"message": "Not found!"})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
