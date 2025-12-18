from sqlalchemy import create_engine, Integer, String,DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from datetime import datetime


class Base(DeclarativeBase):
    pass


# 2) Engine
DB_URL = "sqlite:///example.db"
engine = create_engine(DB_URL, future=True, echo=False)

# 3) Session factory
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


# 4) Helper functions
def init_db() -> None:
    Base.metadata.create_all(bind=engine)

def get_session():
    return SessionLocal()


# 5) Example model
class student(Base):
    __tablename__ = "student"

    id: Mapped[int] = mapped_column(Integer, primary_key=True,autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    scores_relationship= relationship("student",back_ppulates="scores")

class student(Base):
    __tablename__ = "student"

    student_id: Mapped[int] = mapped_column(foreign_key(Integer, primary_key=True,autoincrement=True))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    scores_relationship= relationship("student",back_ppulates="scores")


init_db()
db=get_session()
s1=student(name="hanna",grade_level=7)
s2=student(name="abel",grade_level=11)
db.add(s1)
db.add(s2)
db.commit()
print(db.query(student).all())

h=db.query(student).filter_by(name="hanna").first()
h.grade_level=12
db.commit()
db.delete(s2)
db.commit()
print(db.query(student).all())
db.close