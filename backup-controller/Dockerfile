FROM python:3.12-slim

WORKDIR /controller
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cronjob_spec.py controller.py ./

# непривілейований користувач
USER 65534:65534
CMD ["python", "controller.py"]
