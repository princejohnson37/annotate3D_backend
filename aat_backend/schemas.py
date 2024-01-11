from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class UserBase(BaseModel):
    username: str
    firstname: str | None = None
    lastname: str | None = None


class UserCreate(UserBase):
    hashed_password: str


class User(UserBase):
    id: int

    class Config:
        orm_mode = True


class UserAuth(UserBase):
    id: int
    hashed_password: str

    class Config:
        orm_mode = True


class FileBase(BaseModel):
    path: str
    filename: str


class FileCreate(FileBase):
    project_id: str


class File(FileBase):
    id: int
    
    class Config:
        orm_mode = True


class AnnotationBase(BaseModel):
    note: str
    coordinates: dict
    color: str


class AnnotationCreate(AnnotationBase):
    # project_id: str
    pass


class Annotation(AnnotationBase):
    id: int
    # owner: User
    
    class Config:
        orm_mode = True


class ProjectBase(BaseModel):
    name: str


class Project(ProjectBase):
    id: str
    owner: User
    files: list[File] = []
    # annotations: list[Annotation] = []
    shared_users: list[User] = []

    class Config:
        orm_mode = True


class ProjectCreate(ProjectBase):
    pass