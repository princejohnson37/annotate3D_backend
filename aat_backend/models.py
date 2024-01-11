from sqlalchemy import Column, ForeignKey, Integer, String, JSON, Table
from sqlalchemy.orm import relationship

from .database import Base

project_user = Table('project_user', Base.metadata,
    Column('project_id', ForeignKey('projects.id'), primary_key=True),
    Column('user_id', ForeignKey('users.id'), primary_key=True)
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    firstname = Column(String)
    lastname = Column(String)
    hashed_password = Column(String)

    projects = relationship("Project", back_populates="owner")
    annotations = relationship("Annotation", back_populates="owner")
    shared_projects = relationship("Project", secondary="project_user", back_populates='shared_users')

    def dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'hashed_password': self.hashed_password,
        }


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    name = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="projects")
    files = relationship("File", back_populates="project")
    # annotations = relationship("Annotation", back_populates="project")
    shared_users = relationship("User", secondary="project_user", back_populates='shared_projects')


class Annotation(Base):
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True)
    note = Column(String)
    coordinates = Column(JSON)
    color = Column(String)
    project_id = Column(String, ForeignKey("projects.id"))
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="annotations")
    # project = relationship("Project", back_populates="annotations")

    def dict(self):
        return {
            'id': self.id,
            'note': self.note,
            'coordinates': self.coordinates,
            'color': self.color
        }


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True)
    path = Column(String)
    filename = Column(String)
    project_id = Column(String, ForeignKey("projects.id"))

    project = relationship("Project", back_populates="files")
