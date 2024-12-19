FROM python:3.11
RUN useradd -m -s /bin/bash appuser
WORKDIR /code
COPY ./docker/initdb/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./data/. /code/
RUN chown -R appuser:appuser /code
USER appuser
CMD ["python", "data_to_postgis.py"]