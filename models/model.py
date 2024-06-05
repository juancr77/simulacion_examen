from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Float
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Modelo para la tabla 'students'
class Student(Base):
    __tablename__ = 'students'
    student_id = Column(Integer, primary_key=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    matricula = Column(String(20), nullable=False, unique=True)
    password = Column(String(255), nullable=False)

# Modelo para la tabla 'questions2'
class Question2(Base):
    __tablename__ = 'questions2'
    question_id = Column(Integer, primary_key=True, autoincrement=True)
    question_text = Column(String(255), nullable=False)
    options = relationship("Option2", back_populates="question")

# Modelo para la tabla 'options2'
class Option2(Base):
    __tablename__ = 'options2'
    option_id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey('questions2.question_id'))
    option_text = Column(String(255), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    question = relationship("Question2", back_populates="options")
    answers = relationship("Answer2", back_populates="selected_option")

# Modelo para la tabla 'answers2'
class Answer2(Base):
    __tablename__ = 'answers2'
    answer_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.student_id'))
    question_id = Column(Integer, ForeignKey('questions2.question_id'))
    selected_option_id = Column(Integer, ForeignKey('options2.option_id'))
    selected_option = relationship("Option2", back_populates="answers")

# Modelo para la tabla 'resultados2'
class Result2(Base):
    __tablename__ = 'resultados2'
    resultado_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.student_id'))
    puntaje_total = Column(Integer)
    intentos = Column(Integer)
    nivel = Column(String(50))
    aprobado = Column(Boolean)
    score_percentage = Column(Float)
    total_points = Column(Integer)
    student = relationship("Student")


# Modelo para la tabla 'resultados_40'
class Result40(Base):
    __tablename__ = 'resultados_40'
    resultado_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.student_id'))
    puntaje_total = Column(Integer)
    intento = Column(Integer)
    nivel = Column(String(50))
    aprobado = Column(Boolean)
    score_percentage = Column(Float)
    total_points = Column(Float)
    student = relationship("Student")


class Database:
    _instance = None
    _engine = None
    _session = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            # Crea el motor de la base de datos
            cls._engine = create_engine('mysql+pymysql://root:@localhost/examen_ingles', echo=True)
            # Asegura que todas las tablas estén creadas
            Base.metadata.create_all(cls._engine)
            # Crea una sesión factory que será única
            cls._session = sessionmaker(bind=cls._engine)
        return cls._instance

    @classmethod
    def get_session(cls):
        return cls._session()

# Uso de la clase Database
database = Database()
session = database.get_session()
