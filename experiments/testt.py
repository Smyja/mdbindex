import os
import json
from dotenv import load_dotenv

from llama_index.indices.struct_store import SQLContextContainerBuilder
from dbreader import DatabaseReader
from sqlalchemy import create_engine, inspect,Table, Column, Integer, String, MetaData, Text
from llama_index import GPTSQLStructStoreIndex, SQLDatabase,Document
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
user = 'akposlive59@gmail.com' # your Mindsdb Cloud email address is your username
password = '101Akpobi$$' # replace this value
host = 'cloud.mindsdb.com'
port = 3306
database = 'd'
engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
sql_database = SQLDatabase(engine)
reader = DatabaseReader(engine=engine)

query = f"""
SELECT * FROM files.mdb;
"""
documents = reader.load_data(query=query)
# create an inspector object



# Load the JSON file and parse it into a dictionary
with open('do_text.json', 'r') as f:
    data_list = json.load(f)

# Infer the column names and data types from the first dictionary in the list
columns = []
for col_name, col_value in data_list[0].items():
    if isinstance(col_value, int):
        columns.append(Column(col_name, Integer))
    else:
        columns.append(Column(col_name, Text))

# Define the table using SQLAlchemy's Table class
metadata = MetaData()
my_table = Table('my_table', metadata, *columns)

# Create the table using SQLAlchemy's create_all method
metadata.create_all(engine)

sql_database = SQLDatabase(engine, include_tables=["my_table"])

sql_database.table_info
inspector = inspect(engine)

# retrieve the list of table names
table_names = inspector.get_table_names()

# print the table names
print(table_names)
# print(documents)
# city_stats_text = (
#     "This table gives information regarding the mindsdb documentation along with sources and references and page links.\n"
# )
# context_documents_dict = {"city_stats": [Document(city_stats_text)]}
# context_builder = SQLContextContainerBuilder.from_documents(
#     context_documents_dict, 
#     sql_database
# )
# context_container = context_builder.build_context_container()

# index = GPTSQLStructStoreIndex.from_documents(
#     documents, 
#     sql_database=sql_database, 
#     table_name="",
#     sql_context_container=context_container,
# )
# response = index.query("What is mindsdb?", mode="default")