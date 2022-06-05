import pandas as pd
import psycopg2
from sqlalchemy import create_engine

#conn_string = f'postgresql://postgres:postgres@0.0.0.0:5432/atforestry'
#db = create_engine(conn_string)
#conn = db.connect()
        
data = pd.read_csv('data.csv')

sqlinsert = data.to_sql()

#data.to_sql('prediction', con=conn, if_exists='append',
#        index=False)

#conn.close()
print(sqlinsert)