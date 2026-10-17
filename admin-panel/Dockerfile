FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=Europe/Istanbul
WORKDIR /app
COPY requirements.txt requirements-bots.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-bots.txt
COPY adminpanel ./adminpanel
COPY botkit ./botkit
COPY bots ./bots
EXPOSE 8090
CMD ["uvicorn", "adminpanel.web:app", "--host", "0.0.0.0", "--port", "8090", "--proxy-headers"]
