from builtins import breakpoint
import os
import json
import urllib.request
from app.utils import generate_raster_png_files, list_files_in_directory, predict_raster_deforestation_category, get_coordinate_from_metadata
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
import psycopg2
import logging
from logging.config import dictConfig
from app.log_config import log_config 
from io import StringIO

dictConfig(log_config)
logger = logging.getLogger("planet_api_logger")

DB_URL = os.getenv('DB_URL')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

conn = psycopg2.connect(
    host=DB_URL,
    port=5432,
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    database=POSTGRES_DB) 

class PlanetAPI():
    def __init__(self, api_key, api_url):
        self.api_key = api_key
        self.api_url = api_url

class Mosaic():
    def __init__(self, name, session, url):
        self.name = name
        self.session = session
        self.url = url
        self.api_name = name + '_date_mosaic'

    def set_mosaic_id(self):
        """
        Returns mosaic_id if exists
        """ 

        global conn

        #create postgres connection

        firstDay = datetime.date.today().replace(day=1)
        
        i = 10
        while i > 0:
            logger.info("Searching for mosaic id firstDay = " + firstDay.strftime("%Y-%m-%d"))
            yearMonth = firstDay.strftime('%Y-%m')
            self.api_name = self.name + '_' + yearMonth + '_mosaic'

            #create headers
            parameters = {
            "name__is" :self.api_name
            }

            #request access to basemaps
            res = self.session.get(url = self.url, params = parameters)

            mosaic = res.json()
            print(str(mosaic))

            if len(mosaic['mosaics']) > 0:
                self.date = yearMonth

                cur = conn.cursor()

                cur.execute(f'SELECT * FROM prediction WHERE predictiontimestamp = \'{firstDay} 00:00:00\'') 
                rows = cur.fetchall()

                if len(rows) == 0:
                    break 
                else:
                    firstDay = firstDay - relativedelta(months=1)    
            else:
                firstDay = firstDay - relativedelta(months=1)
            i = i - 1

        mosaic_id = mosaic['mosaics'][0]['id']
        self.id = mosaic_id
        logger.info('Mosaic found. Mosaic id = ' + str(mosaic_id))

        return None
    
    def get_quads_from_mosaic(self, bbox:str):
        """
        Gets quads from mosaic data

        Args:
            mosaic_id (str): Id of the mosaic that was pulled
            bbox (str): Bounding Box to target for quads

        Returns:
            quads = dict: dictionary with quads data
        """

        self.bbox = bbox

        search_parameters = {
        'bbox': bbox,
        'minimal': True
        }
        #accessing quads using metadata from mosaic
        quads_url = "{}/{}/quads".format(self.url, self.id) 
        res = self.session.get(quads_url, params=search_parameters, stream=True)
        quads = res.json()

        #Store Mosaic metadata data
        for quad in quads['items']:
            quad['mosaic_id']=self.id
            quad['master_bbox']=self.bbox
            quad['mosaic_name']=self.name
            quad['mosaic_date']=self.date
            break

        self.quads=quads
        return None

    def store_quads_metadata(self, path:str=os.path.join('src','data','mosaics'))->bool:
        """Stores quads metadata

            Args:
                quads (dict): Quads data
                path (str): Path to save the metadata

            Returns:
                bool: Returns True
        """    

        #check if directory exists, if not create it
        if not os.path.exists(path):
                os.makedirs(path)

        data_path = os.path.join(path,'planet_metadata.json')

        #check if file exists
        if os.path.exists(data_path)==False:
            with open(os.path.join(data_path),'w+') as f:
                f.write(json.dumps([]))

        with open(data_path, "r+", encoding="utf-8") as f: #r+ is for reading and writing
            results = json.loads(f.read())
            if results == []:
                results.append(self.quads['items'])
                f.seek(0) #Move across bytes of the file to insure you are at the start
                f.write(json.dumps(results[0]))
            else:
                results.append(self.quads['items'])
                f.seek(0) #Move across bytes of the file to insure you are at the start
                f.write(json.dumps(results))

        return None

    def download_quads_tiff(self, path:str=os.path.join('src','data','mosaics'))->bool:
        
        print(os.getcwd())

        #check if directory exists, if not create it
        if not os.path.exists(path):
                os.makedirs(path)

        #Create directory with mosaic_name
        if not os.path.exists(os.path.join(path,self.id)):
                os.makedirs(os.path.join(path,self.id))

        items = self.quads['items']

        #Iterate dict and start saving
        for i in items:
            link = i['_links']['download']
            name = i['id']
            name = name + '.tiff'
            filename = os.path.join(path,self.id,name)

            #checks if file already exists before s
            if not os.path.isfile(filename):
                urllib.request.urlretrieve(link, filename)
        
        return True

    def generate_raster_files(self):
        tiff_files = list_files_in_directory(os.path.join('src','data','mosaics',self.id))
        for tiff_file in tiff_files:
            logger.info('Generating raster file for ' + tiff_file)
            generate_raster_png_files(tiff_file=tiff_file,mosaic_code=self.id, path='src/data/mosaics/')
        return None

    def run_inference_predictions(self):

        global conn

        #Get path
        main_path = os.path.join('src','data', 'mosaics')
        #initialize Datframe
        data = pd.DataFrame(columns=["sqbl_longitude", "sqbl_latitude","sqtr_longitude", "sqtr_latitude", "prediction", "roster", "tiff_code", "mosaic"])

        #list tiff folfers in mosaic folders
        tiff_folders = os.listdir(os.path.join(main_path,self.id))

        for tiff_folder_name in tiff_folders:
            #if is a directory
            if os.path.isdir(os.path.join(main_path, self.id, tiff_folder_name)):
                #for roster in tiff
                for roster in list_files_in_directory(os.path.join(main_path, self.id, tiff_folder_name)):
                    
                    roster_path = os.path.join(main_path, self.id, tiff_folder_name, roster)
                    logger.info('Predicting '+roster_path)
                    prediction = predict_raster_deforestation_category(path=roster_path)
                    logger.info('prediction = '+prediction)
                    
                    # coordinates

                    coordinates = get_coordinate_from_metadata(mosaic_id=self.id, tiff_id=tiff_folder_name)

                    #Prediction tame

                    date = self.date
                    date_list = date.split('-')
                    prediction_date = datetime.date(year=int(date_list[0]),month=int(date_list[1]),day=1)

                    if not coordinates:
                        bl_lng = 0
                        bl_lat = 0
                        tr_lng = 0
                        tr_lat = 0
                    else:
                        bl_lng = coordinates[0]
                        bl_lat = coordinates[1]
                        tr_lng = coordinates[2]
                        tr_lat = coordinates[3]

                    entry = pd.DataFrame.from_dict({
                        "sqbl_longitude": [bl_lng],
                        "sqbl_latitude": [bl_lat],
                        "sqtr_longitude": [tr_lng],
                        "sqtr_latitude": [tr_lat],
                        "prediction": prediction,
                        "predictiontimestamp":prediction_date,
                        "tiff_code": tiff_folder_name,
                        "roster":os.path.basename(roster_path)[:-4],
                        "mosaic": self.id
                    })

                    data = pd.concat([data, entry], ignore_index=True)

        #write to dataframe
        data.to_csv(os.path.join('src','data','data.csv'), index=False)

        cursor = conn.cursor()
        cursor.execute("SELECT setval('prediction_id_seq', (SELECT max(id) FROM prediction))")
        
        f = StringIO()
        items = []

        for (idx, row) in data.iterrows():
            value = (row['sqbl_longitude'], row['sqbl_latitude'], row['sqtr_longitude'], row['sqtr_latitude'], row['prediction'], row['predictiontimestamp'], row['tiff_code'], row['roster'], row['mosaic'])
            items.append('\t'.join(map(str, value))+'\n')

        f.writelines(items)
        f.seek(0)

        cursor.copy_from(f, 'prediction', columns=('sqbl_longitude', 'sqbl_latitude', 'sqtr_longitude', 'sqtr_latitude', 'prediction', 'predictiontimestamp', 'tiff_code', 'roster', 'mosaic'))

        f.close()

        conn.commit()
        cursor.close()    
                    
                    


                    



            

