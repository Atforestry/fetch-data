from socket import close
import pandas as pd
import psycopg2
from io import StringIO

conn = psycopg2.connect(host='0.0.0.0',
                        port=5432,
                        user='postgres',
                        password='postgres',
                        database='atforestry') 

data = pd.read_csv('april-2022-data.csv')
cursor = conn.cursor()
f = StringIO()
items = []

for (idx, row) in data.iterrows():
  value = (row['sqbl_longitude'], row['sqbl_latitude'], row['sqtr_longitude'], row['sqtr_latitude'], row['prediction'], row['predictiontimestamp'], row['tiff_code'], row['roster'], row['mosaic'])
  items.append('\t'.join(map(str, value))+'\n')

f.writelines(items)
f.seek(0)

cursor.copy_from(f, 'prediction', columns=('sqbl_longitude', 'sqbl_latitude', 'sqtr_longitude', 'sqtr_latitude', 'prediction', 'predictiontimestamp', 'tiff_code', 'roster', 'mosaic'))

conn.commit()
cursor.close()    
conn.close()
f.close()
