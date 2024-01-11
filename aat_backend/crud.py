import uuid
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from passlib.hash import bcrypt

from . import models, schemas


def get_user_auth(db: Session, username: str):
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if db_user:
        return schemas.UserAuth(**db_user.dict())
    else:
        return False

def get_user(db: Session, username: str):
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if db_user:
        return schemas.User(**db_user.dict())
    else:
        return False

def create_user(db: Session, user: schemas.UserCreate):
    user.hashed_password = bcrypt.hash(user.hashed_password)
    db_user = models.User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_projects(db: Session, user: schemas.User):
    projects = db.query(models.Project).filter(
        (models.Project.owner_id == user.id) |
        (models.Project.shared_users.any(id=user.id))
    ).all()
    return projects

def get_project(db: Session, project_id):
    return db.query(models.Project).filter(models.Project.id == project_id).first()

def create_project(db: Session, project: schemas.ProjectCreate, user: schemas.User):
    db_project = models.Project(**project.dict())
    db_project.owner_id = user.id
    db_project.id = str(uuid.uuid4())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def get_file(db: Session, file_id: int):
    return db.query(models.File).filter(models.File.id == file_id).first()

def create_file(db: Session, file: schemas.FileCreate):
    db_file = models.File(**file.dict())
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def delete_file(db: Session, file: models.File):
    db.delete(file)
    db.commit()
    
def create_annotation(db: Session, annotation: schemas.AnnotationCreate, user: schemas.User, project_id: str):
    db_annotation = models.Annotation(**annotation.dict())
    db_annotation.owner_id = user.id
    db_annotation.project_id = project_id
    db.add(db_annotation)
    db.commit()
    db.refresh(db_annotation)
    return db_annotation

def get_annotations(db: Session, project_id: str):
    return db.query(models.Annotation).filter(models.Annotation.project_id == project_id).all()

def get_annotation(db: Session, annotation_id: str):
    return db.query(models.Annotation).filter(models.Annotation.id == annotation_id).first()

def update_annotation(db: Session, annotation_id: int, annotation: schemas.AnnotationCreate):
    existing_annotation = db.query(models.Annotation).filter(models.Annotation.id == annotation_id).first()

    if existing_annotation:
        for field, value in annotation.dict().items():
            setattr(existing_annotation, field, value)

        db.commit()

    return existing_annotation

def delete_annotation(db: Session, annotation: models.Annotation):
    db.delete(annotation)
    db.commit()

def add_shared_user(db: Session, user: schemas.User, project_id: str):
    try:
        db.execute(models.project_user.insert().values(project_id=project_id, user_id=user.id))
        db.commit()
    except IntegrityError:
        db.rollback()