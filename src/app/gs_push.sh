#!/bin/bash

gcloud auth activate-service-account atforestry@atforestry.iam.gserviceaccount.com --key-file=/app/google.json --project=atforestry && gsutil -m cp -r /app/src/data/mosaics/ gs://atforestry-model-tracker/planet_data
