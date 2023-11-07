import os

import boto3
from botocore.config import Config
from celery import Celery
from dotenv import load_dotenv

from toktik_chunker.video_chunker import download_file_from_s3, split_video, upload_chunked_to_s3


def create_celery_app():
    load_dotenv()
    internal_app = Celery("chunker",
                          broker=f"redis://"
                                 f"{os.environ.get('REDIS_HOSTNAME', 'localhost')}"
                                 f":{os.environ.get('REDIS_PORT', '6381')}"
                                 f"/1",
                          backend=f"redis://"
                                  f"{os.environ.get('REDIS_HOSTNAME', 'localhost')}"
                                  f":{os.environ.get('REDIS_PORT', '6381')}"
                                  f"/1",
                          broker_connection_retry_on_startup=True)
    return internal_app


app = create_celery_app()


@app.task
def do_chunking(object_name):
    load_dotenv()
    client = boto3.client(
        "s3",
        region_name=os.environ.get("S3_REGION"),
        endpoint_url=os.environ.get("S3_RAW_ENDPOINT"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY"),
        aws_secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY"),
        config=Config(s3={"addressing_style": "virtual"}, signature_version="v4"),
    )

    try:
        downloaded_file = download_file_from_s3(client, object_name)
        converted_file = split_video(downloaded_file, os.environ.get('CHUNK_LENGTH_SECONDS', 2))
        return upload_chunked_to_s3(client, converted_file)
    except Exception as e:
        print(e)
        return False
