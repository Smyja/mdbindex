from typing import Any, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from llama_index.langchain_helpers.sql_wrapper import SQLDatabase
from llama_index.readers.base import BaseReader
from llama_index.readers.schema.base import Document


class DatabaseReader(BaseReader):
    """Simple Database reader.

    Concatenates each row into Document used by LlamaIndex.

    Args:
        engine (Optional[Engine]): SQLAlchemy Engine object of the database connection.
        uri (Optional[str]): uri of the database connection.
        scheme (Optional[str]): scheme of the database connection.
        host (Optional[str]): host of the database connection.
        port (Optional[int]): port of the database connection.
        user (Optional[str]): user of the database connection.
        password (Optional[str]): password of the database connection.
        dbname (Optional[str]): dbname of the database connection.

    Returns:
        DatabaseReader: A DatabaseReader object.
    """

    def __init__(
        self,
        engine: Optional[Engine] = None,
        uri: Optional[str] = None,
        scheme: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        dbname: Optional[str] = None,
        *args: Optional[Any],
        **kwargs: Optional[Any],
    ) -> None:
        """Initialize with parameters."""
        if engine is not None:
            self.sql_database = SQLDatabase(engine, *args, **kwargs)
        elif uri is not None:
            self.uri = uri
            self.sql_database = SQLDatabase.from_uri(uri, *args, **kwargs)
        elif all(param is not None for param in [host, user, password]):
            url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{dbname}"
            self.sql_database = SQLDatabase(create_engine(url), *args, **kwargs)
        else:
            raise ValueError(
                "You must provide either a SQL Alchemy Engine, a valid connection URI, or a valid "
                "set of credentials."
            )

    def load_data(self, query: str) -> List[Document]:
        """Query and load data from the Database, returning a list of Documents.

        Args:
            query (str): Query parameter to filter tables and rows.

        Returns:
            List[Document]: A list of Document objects.
        """
        documents = []
        with self.sql_database.engine.connect() as connection:
            if query is None:
                raise ValueError("A query parameter is necessary to filter the data")
            else:
                result = connection.execute(query)

            for item in result.fetchall():
                # fetch each item
                doc_str = ", ".join([str(entry) for entry in item])
                documents.append(Document(doc_str))
        return documents
