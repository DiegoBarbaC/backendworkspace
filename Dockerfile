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
EXPOSE 5000

# Comando para ejecutar la aplicación
CMD ["python", "app.py"]