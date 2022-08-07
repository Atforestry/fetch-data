#!/bin/bash

gcloud auth activate-service-account atforestry@atforestry.iam.gserviceaccount.com --key-file=./google.json --project=atforestry
gsutil cp -r ./src/data/mosaics/ gs://atforestry-model-tracker/planet_data
