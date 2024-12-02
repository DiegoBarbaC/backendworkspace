# Imagen base de Python
FROM python:3.9-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar pipenv
RUN pip install pipenv

# Copiar los archivos de dependencias
COPY Pipfile Pipfile.lock ./

# Instalar dependencias
RUN pipenv install --system --deploy

# Copiar el resto del código
COPY . .

# Exponer el puerto que usa Flask
EXPOSE 8000

# Establecer las variables de entorno
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Comando para ejecutar la aplicación
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]

