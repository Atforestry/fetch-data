#!/bin/bash
chmod u+x src/app/gs_push.sh
uvicorn src.main:app --host=0.0.0.0 --port 8000 --reload