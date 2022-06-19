import subprocess
import os
import json
import numpy as np
from telluric.georaster import GeoRaster2
from PIL import Image
import tensorflow as tf
from os import listdir
from os.path import isfile, join
import matplotlib.pyplot as plt
import numpy as np
import cv2
import requests
import pandas as pd




def imshow(inp, fig_size=4, title=None):
    """Imshow for Tensor."""
    inp = inp.numpy().transpose((1, 2, 0))
    mean = np.array([0.485, 0.456, 0.406])
    std = np.array([0.229, 0.224, 0.225])
    inp = std * inp + mean
    inp = np.clip(inp, 0, 1)

    fig, ax = plt.subplots(figsize=(fig_size, fig_size))
    ax.imshow(inp)
    
def transform(image, mean, std):
    for channel in range(3):
        image[:,:,channel] = (image[:,:,channel] - mean[channel]) / std[channel]
    return image

def list_files_in_directory(path:str):
    onlyfiles = [f for f in listdir(path) if isfile(join(path, f))]
    return onlyfiles

# Processing Images
def preprocess_raster_image(raster):
    # Move channels from start of array (e.g. (C, H, W)) to the end (e.g. (H, W, C))
    image_original = np.einsum('ijk->jki', raster.image)[:, :, :3]

    # Stretch each channel to min/max for later converting the image to np.uint8
    image = image_original.astype(float)
    for idx_channel in range(image.shape[-1]):
        image_min = image[..., idx_channel].min()
        image_max = image[..., idx_channel].max()
        image[..., idx_channel] = (image[..., idx_channel] - image_min) * (255 / (image_max - image_min))

    image = cv2.convertScaleAbs(image)

    return image

def generate_raster_png_files(tiff_file:str, mosaic_code:str, path:str):
    tiff_path = os.path.join(path, mosaic_code,tiff_file)
    raster = GeoRaster2.open(tiff_path)
    
    ## See raster chunks
    i=1
    for chunk in raster.chunks(224):
        raster = chunk.raster
        converted_raster = preprocess_raster_image(raster)
        img = tf.image.resize(converted_raster, [256,256])
        img = tf.image.central_crop(img, central_fraction=224/256)
        img = tf.cast(img, np.uint8).numpy()
        img = Image.fromarray(img, 'RGB')
        i=i+1
        #img.show()
        #check if directory exists, if not create it
        file_path = os.path.join(path, mosaic_code)
        tiff_folder = os.path.join(file_path, tiff_file[:-5])
        #Create directory
        if not os.path.exists(tiff_folder):
            os.mkdir(tiff_folder)
        #Save file
        tiff_file_path = os.path.join(tiff_folder,f'{i}.png')
        img.save(tiff_file_path)

def get_raster_image_path(bbox:list, mosaic_date:str, raster_location:int):
    main_path = os.path.join('src','data', 'mosaics')
    meta_data_path = os.path.join(main_path,'planet_metadata.json')

    #Read metadata
    with open(meta_data_path, 'r') as f:
        planet_meta_data = json.load(f)

    for item in planet_meta_data:
        if item['bbox']==bbox and item['mosaic_date']==mosaic_date:
            raster_path = os.path.join(item['mosaic_id'],item['id'],str(raster_location)+'.png')
            full_roster_path = os.path.join(main_path, raster_path)
            return full_roster_path

def get_coordinate_from_metadata(mosaic_id:str, tiff_id:str):
    main_path = os.path.join('src','data', 'mosaics')
    meta_data_path = os.path.join(main_path,'planet_metadata.json')

    #Read metadata
    with open(meta_data_path, 'r') as f:
        planet_meta_data = json.load(f)

    for item in planet_meta_data:
        if item.has_key('mosaic_id') and item['mosaic_id']==mosaic_id and item.has_key('id') and item['id']==tiff_id:
            return item['bbox']

def predict_raster_deforestation_category(path:str):
    MODEL_PREDICT_URL= os.environ.get('MODEL_PREDICT_URL')
    url = f"http://{MODEL_PREDICT_URL}/v1/predict_image_label"
    #url = "http://35.223.171.201:8020/v1/predict_image_label"
    payload={}
    
    files=[
    ('file',(os.path.basename(path),open(path,'rb'),'image/png'))
    ]
    headers = {}
    response = requests.request("POST", url, headers=headers, data=payload, files=files)
    print(response)
    return response.text

def push_to_gcp():
    """Push data into GCP bucket"""
    subprocess.call(["./src/app/gs_push.sh"])



    






        