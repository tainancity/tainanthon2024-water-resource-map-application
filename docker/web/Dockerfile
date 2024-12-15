FROM python:3.11
WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./web/app.py /code/app.py
CMD ["gunicorn", "-b", "0.0.0.0:8888", "app:server"]