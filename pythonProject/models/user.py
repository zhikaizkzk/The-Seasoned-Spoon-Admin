from enum import Enum
from sqlalchemy import Column, Integer, String, Enum as SQLEnum
from database.session import Base


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"


class User(Base):
    __tablename__ = "app_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    role = Column(SQLEnum(RoleEnum), nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, first_name={self.first_name}, last_name={self.last_name}, role={self.role})>"
