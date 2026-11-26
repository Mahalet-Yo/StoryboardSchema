# Reproducible runtime for the pipeline: Python 3.12, FFmpeg with libass, the fonts the
# subtitles and end card use. Models run remotely (Gemini, Cloudflare, HF Space), so no GPU.
#   docker build -t heritage-short .
#   docker run --rm --env-file .env -v "$PWD:/app" heritage-short film
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core fonts-noto-core git make \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# The repo is mounted at run time in normal use; this copy makes the image work on its own too.
RUN git config --global --add safe.directory /app

ENTRYPOINT ["python", "-m", "pipeline"]
CMD ["film"]
