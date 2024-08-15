from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, UniqueConstraint, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now())

    words = relationship('UserWord', back_populates='user')


class Word(Base):
    __tablename__ = 'words'
    word_id = Column(Integer, primary_key=True)
    target_word = Column(String(255), nullable=False)
    translate_word = Column(String(255), nullable=False)

    __table_args__ = (UniqueConstraint('target_word', 'translate_word'),)


class UserWord(Base):
    __tablename__ = 'user_words'
    user_word_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    word_id = Column(Integer, ForeignKey('words.word_id'))

    user = relationship('User', back_populates='words')
    word = relationship('Word')

    __table_args__ = (UniqueConstraint('user_id', 'word_id'),)


username = ''
password = ''
dbname = ''

DSN = f'postgresql+psycopg2://{username}:{password}@localhost:5432/{dbname}'

engine = create_engine(DSN)
Session = sessionmaker(bind=engine)
session = Session()

def initialize_database():
    Base.metadata.create_all(engine)
    words = [
        ('Green', 'Зеленый'),
        ('Every', 'Каждый'),
        ('He', 'Он'),
        ('Country', 'Страна'),
        ('Question', 'Вопрос'),
        ('Tree', 'Дерево'),
        ('They', 'Они'),
        ('Week', 'Неделя'),
        ('Head', 'Голова'),
        ('Fire', 'Огонь')
    ]
    for target_word, translate_word in words:
        word = Word(target_word=target_word, translate_word=translate_word)
        session.add(word)
    session.commit()
