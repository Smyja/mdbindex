import os
import json
from dotenv import load_dotenv
from llama_index.indices.struct_store import SQLContextContainerBuilder
from dbreader import DatabaseReader
from sqlalchemy import create_engine
from llama_index import GPTSimpleVectorIndex
from langchain.chains.question_answering import load_qa_chain
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
user = os.getenv("user")
password = os.getenv("password")
host = os.getenv("host")
port = os.getenv("port")
database = os.getenv("database") #database can be anything
engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
reader = DatabaseReader(engine=engine)

query = f"""
SELECT CONCAT('[', GROUP_CONCAT(JSON_OBJECT('id', id, 'title', title, 'page_link', page_link, 'text', text)), ']')
FROM files.mdb;
"""
documents = reader.load_data(query=query)
# index = GPTSimpleVectorIndex.from_documents(documents)
# index.save_to_disk('mdb.json')
#  load from disk
index = GPTSimpleVectorIndex.load_from_disk('mdb.json')
response=index.query('what is mindsdb? provide references and sources')
print(response)

