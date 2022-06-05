import pandas as pd
import psycopg2

conn_string = f'postgresql://postgres:postgres@db:5432/atforestry'
db = create_engine(conn_string)
conn = db.connect()
        
data = pd.read_csv('data.csv')

data.to_sql('data', con=conn, if_exists='append',
        index=False)

conn.close()