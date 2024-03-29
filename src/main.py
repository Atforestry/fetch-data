
import sys
import os
sys.path.insert(1, './src')

from fastapi import FastAPI, status
from fastapi.responses import HTMLResponse, FileResponse
from app.utils import get_raster_image_path, predict_raster_deforestation_category,push_to_gcp
from app.views import PlanetAPI, Mosaic
import logging
from logging.config import dictConfig
from app.log_config import log_config 
import requests

dictConfig(log_config)
logger = logging.getLogger("planet_api_logger")

app = FastAPI(
    title='Atforesty Planet Batch Run Service',
    description='This API allows to fetch data from the Planet interface',
    version="1.0.0")

PLANET_API_KEY = os.environ.get('PLANET_API_KEY')
PLANET_URL = "https://api.planet.com/basemaps/v1/mosaics"

@app.get('/healthcheck', status_code=status.HTTP_200_OK)

@app.get("/")
async def main():
    content = """
<body>
<p>Atforestry Planet Fetch Data!!</p>
</body>
    """
    return HTMLResponse(content=content)

@app.on_event("startup")
def startup_event():
    """Authenticates to Planet API

    Raises:
        SystemError: If no PLANET_API_KEY is provided
    """    
    global planet_api
    planet_api = PlanetAPI(PLANET_API_KEY, PLANET_URL)
    #setup session
    global session
    session = requests.Session()
    #authenticate
    if planet_api.api_key == None:
        raise SystemError('environment PLANET_API_KEY variable is empty!!')

    session.auth = (planet_api.api_key, "")

@app.get("/v1/check_planet_connection")
def check_connection():
    """Checks connection status tu planet API

    Returns:
        res.status_code: Response should be 200
    """    
    parameters = {
    "name__is" :'planet_medres_normalized_analytic_1month_mosaic'
    }

    res = session.get(planet_api.api_url, params = parameters)
    logger.info("Health connection to Planet ")
    return {'response':res.status_code,
            'description':'acces confirmed'
    }

@app.get("/v1/fetch_mosaics")
def fetch_mosaics():
    
    # We fix these variables. If this needs to be changed, 
    # we can add them to our .env file so we don't need to
    # change the code.

    mosaic_name = "planet_medres_normalized_analytic"
    bbox = "-53,-4,-52,-3"

    mosaic = Mosaic(name = mosaic_name, session=session, url=planet_api.api_url)
    #Set the mosaic id
    mosaic.set_mosaic_id()
    #Get the quads
    mosaic.get_quads_from_mosaic(bbox=bbox)
    #Download quads
    logger.info("Requesting quads tiffs")
    mosaic.download_quads_tiff()
    #Store metadata
    logger.info("Pushing metadata")
    mosaic.store_quads_metadata()   
    #Store rgb rasters
    logger.info("Converting tiff to rgb files")    
    mosaic.generate_raster_files()
    logger.info("Files Generated")   
    #Run Predicitions
    logger.info("Run Predictions") 
    mosaic.run_inference_predictions()  
    logger.info('Pushing to GCP')
    push_to_gcp() 
    return {'status': 'success'}

@app.get("/v1/get_raster_image")
def gest_raster_image(bbox:str, date:str, raster_location:int):
    bbox=bbox.split(',')
    bbox = [float(i) for i in bbox]
    print(bbox)
    file_path = get_raster_image_path(bbox=bbox, mosaic_date=date, raster_location=raster_location)   
    return FileResponse(file_path)

@app.post("/v1/predict_raster_image")
def post_raster_image(bbox:str, date:str, raster_location:int):
    bbox=bbox.split(',')
    bbox = [float(i) for i in bbox]
    file_path = get_raster_image_path(bbox=bbox, mosaic_date=date, raster_location=raster_location)   
    prediction = predict_raster_deforestation_category(path=file_path)
    return {'prediction': prediction}

@app.get("/v1/push_to_gcp")
def pushtogcp(): 
    push_to_gcp()
    return {'res': 'ok'}

