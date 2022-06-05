#!/bin/bash

gcloud auth activate-service-account 411650743689-compute@developer.gserviceaccount.com --key-file=./mlops-3-c0ecd4f26897.json --project=mlops-3
gsutil cp -r ./src/data/mosaics/ gs://atforestry-model-tracker/planet_data
