from sqlalchemy import create_engine

user = 'akposlive59@gmail.com' # your Mindsdb Cloud email address is your username
password = '101Akpobi$$' # replace this value
host = 'cloud.mindsdb.com'
port = 3306
database = ''
print()
def establish_connection():
        engine =  create_engine(url=f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}")
        return engine
try:
        engine = establish_connection()
        with engine.connect() as eng:
                query = eng.execute("SELECT * FROM files.mdb LIMIT 5;")
                for row in query:
                        print(row)
except Exception as e:
        print("Couldn't connect to the database:\n",e)
