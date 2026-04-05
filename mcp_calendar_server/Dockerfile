FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY mcp_calendar_server /app/mcp_calendar_server
ENV PYTHONPATH=/app
EXPOSE 8002

CMD ["uvicorn", "mcp_calendar_server.app.main:app", "--host", "0.0.0.0", "--port", "8002"]
