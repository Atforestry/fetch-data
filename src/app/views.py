from builtins import breakpoint
import os
import json
import urllib.request
from app.utils import generate_raster_png_files, list_files_in_directory, predict_raster_deforestation_category, get_coordinate_from_metadata
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine
import psycopg2
import logging
from logging.config import dictConfig
from app.log_config import log_config 

dictConfig(log_config)
logger = logging.getLogger("planet_api_logger")

PLANET_API_KEY = os.environ.get('PLANET_API_KEY')
PLANET_URL = "https://api.planet.com/basemaps/v1/mosaics"
DB_URL = os.getenv('DB_URL')
POSTGRES_DB = os.getenv('POSTGRES_DB')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')

class PlanetAPI():
    def __init__(self, api_key=PLANET_API_KEY, api_url=PLANET_URL):
        self.api_key = api_key
        self.api_url = api_url
        print(api_url+" "+api_key)

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

        #create postgres connection

        conn = psycopg2.connect(
            host=os.environ['DB_URL'],
            database=os.environ['POSTGRES_DB'],
            user=os.environ['POSTGRES_USER'],
            password=os.environ['POSTGRES_PASSWORD'])
                    
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

        conn.close()

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
                os.mkdir(path)

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
                os.mkdir(path)

        #Create directory with mosaic_name
        if not os.path.exists(os.path.join(path,self.id)):
                os.mkdir(os.path.join(path,self.id))

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
            generate_raster_png_files(tiff_file=tiff_file,mosaic_code=self.id, path='src/data/mosaics/')
        return None

    def run_inference_predictions(self):
        #Get path
        main_path = os.path.join('src','data', 'mosaics')
        #initialize Datframe
        data = pd.DataFrame(columns=["sqbl_longitude", "sqbl_latitude","sqtr_longitude", "sqtr_latitude", "prediction", "roster", "tiff_code", "mosaic"])
        #create postgres connection
        conn_string = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_URL}/{POSTGRES_DB}'
        db = create_engine(conn_string)
        conn = db.connect()
        
        #list tiff folfers in mosaic folders
        tiff_folders = os.listdir(os.path.join(main_path,self.id))

        for tiff_folder_name in tiff_folders:
            #if is a directory
            if os.path.isdir(os.path.join(main_path, self.id, tiff_folder_name)):
                #for roster in tiff
                for roster in list_files_in_directory(os.path.join(main_path, self.id, tiff_folder_name)):
                    
                    roster_path = os.path.join(main_path, self.id, tiff_folder_name, roster)
                    prediction = predict_raster_deforestation_category(path=roster_path)
                    
                    # coordinates

                    coordinates = get_coordinate_from_metadata(mosaic_id=self.id, tiff_id=tiff_folder_name)

                    #Prediction tame

                    date = self.date
                    date_list = date.split('-')
                    prediction_date = datetime.date(year=int(date_list[0]),month=int(date_list[1]),day=1)

                    entry = pd.DataFrame.from_dict({
                        "sqbl_longitude": [coordinates[0]],
                        "sqbl_latitude": [coordinates[1]],
                        "sqtr_longitude": [coordinates[2]],
                        "sqtr_latitude": [coordinates[3]],
                        "prediction": prediction,
                        "predictionTimestamp":prediction_date,
                        "tiff_code": tiff_folder_name,
                        "roster":os.path.basename(roster_path)[:-4],
                        "mosaic": self.id
                    })

                    data = pd.concat([data, entry], ignore_index=True)
                    #write to dataframe
                    data.to_csv(os.path.join('src','data','data.csv'), index=False)

                    #write to postgres
                    data.to_sql('prediction', con=conn, if_exists='append',
                            index=False)
        conn.close()


                    



            

