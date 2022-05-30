FROM python:3.9

WORKDIR /app

COPY requirements.txt ./

RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r requirements.txt


COPY ./src ./src
COPY ./start.sh .

EXPOSE 8000

CMD ["./start.sh"]
