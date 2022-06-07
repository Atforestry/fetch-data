FROM python:3.9

WORKDIR /app

ARG FETCH_DATA_URL=fetch-data:8000
ARG BATCH_RUN_URL=batch-run:8010
ARG MODEL_PREDICTION_URL=model-prediction:8020
ARG USER_QUERY_URL=user-query:80
ARG API_URL=api:8030
ARG DB_URL=db
ARG POSTGRES_DB=atforestry
ARG POSTGRES_USER=postgres
ARG POSTGRES_PASSWORD=postgres
ARG PLANET_API_KEY=

ENV FETCH_DATA_URL $FETCH_DATA_URL
ENV BATCH_RUN_URL $BATCH_RUN_URL
ENV MODEL_PREDICTION_URL $MODEL_PREDICTION_URL
ENV USER_QUERY_URL $USER_QUERY_URL
ENV API_URL $API_URL
ENV DB_URL $DB_URL
ENV POSTGRES_DB $POSTGRES_DB
ENV POSTGRES_USER $POSTGRES_USER
ENV POSTGRES_PASSWORD $POSTGRES_PASSWORD
ENV PLANET_API_KEY $PLANET_API_KEY

COPY requirements.txt ./

RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Downloading gcloud package
RUN curl https://dl.google.com/dl/cloudsdk/release/google-cloud-sdk.tar.gz > /tmp/google-cloud-sdk.tar.gz

# Installing the package
RUN mkdir -p /usr/local/gcloud \
  && tar -C /usr/local/gcloud -xvf /tmp/google-cloud-sdk.tar.gz \
  && /usr/local/gcloud/google-cloud-sdk/install.sh

# Adding the package path to local
ENV PATH $PATH:/usr/local/gcloud/google-cloud-sdk/bin

COPY ./google.json .
COPY ./src/app ./src/app
COPY ./src/main.py ./src
COPY ./start.sh .

EXPOSE 8000

CMD ["./start.sh"]
