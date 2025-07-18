# Imagen base 
FROM --platform=linux/amd64 python:3.10.9-bullseye as base

#Agregar packages requeridos
RUN apt-get update && apt-get -y install wget curl cron vim nano iputils-ping gnupg

#Instalar cliente mongo
RUN wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | apt-key add - && \
    echo "deb http://repo.mongodb.org/apt/debian bullseye/mongodb-org/6.0 main" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list && \
    apt-get update && \
    apt-get install -y mongodb-org-tools mongodb-mongosh

# Establecer el directorio de trabajo
WORKDIR /app

#Timezone
ENV TZ='America/Mexico_City'

# Copiar el resto del código
COPY . .

#Instalar dependencias
RUN pip3 install -r requirements.txt

FROM base as production




