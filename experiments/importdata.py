import pandas as pd
import psycopg2

conn = psycopg2.connect(host='0.0.0.0',
                        port=5432,
                        user='postgres',
                        password='postgres',
                        database='atforestry') 

data = pd.read_csv('april-2021-data.csv')
#data = pd.read_csv('data.csv')
cursor = conn.cursor()

for (idx, row) in data.iterrows():
  cursor.execute("INSERT INTO prediction (sqbl_longitude, sqbl_latitude, sqtr_longitude, sqtr_latitude, prediction, predictiontimestamp, tiff_code, roster, mosaic) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)", 
  (row['sqbl_longitude'], row['sqbl_latitude'], row['sqtr_longitude'], row['sqtr_latitude'], row['prediction'], row['predictiontimestamp'], row['tiff_code'], row['roster'], row['mosaic']))
    
conn.commit()
cursor.close()    
conn.close()