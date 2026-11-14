FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# rasterio wheels link against libexpat; the slim image does not ship it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

# All heavy geo dependencies (rasterio, scipy, h5py, pyogrio) ship manylinux
# wheels, so no GDAL/system build toolchain is needed here.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Lets `python scripts/foo.py` import `app` without a package install.
ENV PYTHONPATH=/app

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
