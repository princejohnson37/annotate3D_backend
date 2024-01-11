import os
import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import FastAPI, HTTPException, Depends, status, WebSocket, WebSocketDisconnect, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext


from . import crud, models, schemas
from .database import engine, get_db


# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY="48d56adc96ef62fd6d10a01ce9da241929b554f4976eed59159fa2a091031b76"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30


models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def authenticate_user(db, username: str, password: str):
    user = crud.get_user_auth(db, username)
    if not user:
        return False
    if not pwd_context.verify(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)]
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = crud.get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs")

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)]
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/user", response_model=schemas.User)
def get_user(current_user: Annotated[schemas.User, Depends(get_current_user)]):
    return current_user

@app.post("/user", response_model=schemas.User)
def create_user(
    user: schemas.UserCreate,
    db: Annotated[Session, Depends(get_db)]
):
    if crud.get_user_auth(db, user.username):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    user_orm = crud.create_user(db, user)
    return user_orm

@app.get("/projects", response_model=list[schemas.Project])
def get_projects(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)]
):
    projects = crud.get_projects(db, current_user)
    return projects

@app.get("/projects/{project_id}", response_model=schemas.Project)
def get_projects(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    project_id: str,
    db: Annotated[Session, Depends(get_db)]
):
    project = crud.get_project(db, project_id)
    if project.owner_id != current_user.id and current_user.id not in project.shared_users:
        crud.add_shared_user(db, current_user, project_id)
    return project

@app.post("/projects")
def create_project(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    project: schemas.ProjectCreate,
    db: Annotated[Session, Depends(get_db)]
):
    project = crud.create_project(db, project=project, user=current_user)
    return project

@app.post("/projects/{project_id}/files")
def create_project_files(
    current_user: Annotated[schemas.User, Depends(get_current_user)],
    project_id: str,
    file: UploadFile,
    db: Annotated[Session, Depends(get_db)]
):
    project = crud.get_project(db, project_id)
    if project:
        uid = str(uuid.uuid4())
        try:
            contents = file.file.read()
            path = f'{uid}{os.path.splitext(file.filename)[1]}'
            with open(os.path.join('data', path), 'wb') as f:
                f.write(contents)
        except Exception:
            return {"message": "There was an error uploading the file"}
        finally:
            file.file.close()
        
        file_sch = schemas.FileCreate(path=path, filename=file.filename, project_id=project_id)
        file_orm = crud.create_file(db, file_sch)
        return file_orm
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

@app.get("/projects/{project_id}/annotations/", response_model=list[schemas.Annotation])
def get_annotations(
    current_user: Annotated[schemas.User, Depends(get_current_user)], 
    project_id: str,
    db: Annotated[Session, Depends(get_db)]
):
    return crud.get_annotations(db, project_id)

@app.post("/projects/{project_id}/annotations/", response_model=schemas.Annotation)
def create_annotations(
    current_user: Annotated[schemas.User, Depends(get_current_user)], 
    project_id: str,
    annotation: schemas.AnnotationCreate, 
    db: Annotated[Session, Depends(get_db)]
):
    annotation = crud.create_annotation(db, annotation=annotation, user=current_user, project_id=project_id)
    return annotation

@app.put("/annotations/{annotation_id}", response_model=schemas.Annotation)
def create_annotations(
    current_user: Annotated[schemas.User, Depends(get_current_user)], 
    annotation_id: str,
    annotation: schemas.AnnotationCreate, 
    db: Annotated[Session, Depends(get_db)]
):
    ann = crud.get_annotation(db, annotation_id)
    if ann:
        if ann.owner_id == current_user.id:
            return crud.update_annotation(db, annotation_id, annotation)
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found")

@app.get("/files/{file_id}")
def get_file(
    # current_user: Annotated[schemas.User, Depends(get_current_user)], 
    file_id: str,
    db: Annotated[Session, Depends(get_db)]
):
    file = crud.get_file(db, file_id)
    if file:
        file_path = os.path.join('data', file.path)
        if os.path.exists(file_path):
            return FileResponse(path=file_path, media_type='application/octet-stream', status_code=status.HTTP_200_OK)
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

@app.delete("/files/{file_id}")
def delete_file(
    current_user: Annotated[schemas.User, Depends(get_current_user)], 
    file_id: str,
    db: Annotated[Session, Depends(get_db)]
):
    file = crud.get_file(db, file_id)
    if file:
        if file.project.owner_id == current_user.id:
            file_path = os.path.join('data', file.path)
            if os.path.exists(file_path):
                os.remove(file_path)
                crud.delete_file(db, file)
                return None
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can delete the files")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

# @app.get("/projects/{project_id}/data")
# def get_project(
#     # current_user: Annotated[schemas.User, Depends(get_current_user)],
#     project_id: int,
#     db: Annotated[Session, Depends(get_db)]
# ):
#     project = crud.get_project(db, project_id=project_id)
#     file_path = os.path.join('data', project.path)
#     if os.path.exists(file_path):
#         return FileResponse(path=file_path, media_type='application/octet-stream', status_code=status.HTTP_200_OK)
#     else:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='File not found')

@app.delete("/annotations/{annotation_id}")
def delete_annotations(
    current_user: Annotated[schemas.User, Depends(get_current_user)], 
    annotation_id: int, 
    db: Annotated[Session, Depends(get_db)]
):
    annotation = crud.get_annotation(db, annotation_id)
    if annotation:
        if annotation.owner_id == current_user.id:
            crud.delete_annotation(db, annotation)
            return None
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Annotation not found")

connected_websockets = set()
latest_message = None
@app.websocket("/projects/{project_id}/annotations")
async def websocket_endpoint(websocket: WebSocket, project_id: str, db: Annotated[Session, Depends(get_db)]):
    global latest_message
    await websocket.accept()
    connected_websockets.add(websocket)
    if latest_message:
        try:
            await websocket.send_json(latest_message)
        except WebSocketDisconnect:
            print("Websocket disconnected")
    try:
        while True:
            message = await websocket.receive_text()
            print(message)
            annotations_orm = crud.get_annotations(db, project_id=project_id)
            annotations = [annotation.dict() for annotation in annotations_orm]
            latest_message = annotations
            for ws in connected_websockets:
                try:
                    print(ws)
                    await ws.send_json(annotations)
                except WebSocketDisconnect:
                    print("Websocket disconnected")
                    connected_websockets.remove(ws)
            # await websocket.send_json(annotations)
            # await asyncio.sleep(5)
    except WebSocketDisconnect:
        print("Websocket disconnected")
    finally:
        connected_websockets.remove(websocket)