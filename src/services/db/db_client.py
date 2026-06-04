from collections.abc import Generator

from sqlmodel import Session, create_engine

from src.config.basic_config import get_config

config = get_config()

engine = create_engine(config.db_url)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
