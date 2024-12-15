FROM python:3.11
WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./api/app.py /code/app.py
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]