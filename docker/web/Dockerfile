FROM python:3.11
RUN useradd -m -s /bin/bash appuser
WORKDIR /code
COPY ./docker/web/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./web/app.py /code/app.py
RUN chown -R appuser:appuser /code
USER appuser
CMD ["gunicorn", "-b", "0.0.0.0:8888", "app:server"]