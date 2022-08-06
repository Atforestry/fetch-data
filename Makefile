export IMAGE_NAME=fetch-data

build:
	docker build . -t atforestry/$(IMAGE_NAME)

run start:
	docker-compose up -d --build
	docker-compose logs -f --tail=20

stop:
	docker-compose down

bash:
	docker run -it atforestry/$(IMAGE_NAME) /bin/bash

logs:
	docker-compose logs -f service


