FROM python:3.11
RUN useradd -m -s /bin/bash appuser
WORKDIR /code
COPY ./docker/fastapi/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./api/app.py /code/app.py
RUN chown -R appuser:appuser /code
USER appuser
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]