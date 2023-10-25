import os
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.client import Config
import shutil
import ffmpeg

def download_file_from_s3(client, object_name):
    file_name, file_extension = object_name.split(".")
    temp_folder = Path("/tmp") / file_name
    temp_folder.mkdir(parents=True, exist_ok=True)

    download_target = Path(f"{temp_folder}/{file_name}.{file_extension}")
    client.download_file(
        os.environ.get("S3_BUCKET_NAME_CONVERTED"), object_name, download_target
    )
    return download_target


def split_video(file_path, chunk_size_seconds):
    file_name, _ = os.path.splitext(file_path)
    try:
        ffmpeg.input(
                file_path
            ).output(
                f"{file_name}.m3u8",
                format="hls",
                hls_time=chunk_size_seconds,
                hls_list_size=0
            ).run(capture_stdout=True, capture_stderr=True)
    
    except ffmpeg.Error as e:
        print('stdout:', e.stdout.decode('utf8'))
        print('stderr:', e.stderr.decode('utf8'))
        raise e
    
    parent_folder = os.path.dirname(file_path) # get parent folder
    os.remove(file_path) # remove mp4 file

    return Path(parent_folder)



def upload_chunked_to_s3(client, folder_path: Path):
    MIMETYPE = {
        "m3u8": "application/x-mpegURL",
        "ts": "	video/mp2t",
    }
    for hls_file in os.listdir(folder_path):
        file_extension = hls_file.split(".")[1].lower()
        mimetype = MIMETYPE.get(file_extension, None)
        if not mimetype:
            continue

        client.upload_file(
            Path(folder_path) / hls_file, # where to get the file
            os.environ.get("S3_BUCKET_NAME_CHUNKED"),
            f"{folder_path.name}/{hls_file}", # where to upload at (with folder)
            ExtraArgs={"ContentType": mimetype, "ACL": "public-read"},
        )

    shutil.rmtree(folder_path)
    return True


if __name__ == "__main__":
    load_dotenv()
    s3_client = boto3.client(
        "s3",
        region_name=os.environ.get("S3_REGION"),
        endpoint_url=os.environ.get("S3_RAW_ENDPOINT"),
        aws_access_key_id=os.environ.get("S3_ACCESS_KEY"),
        aws_secret_access_key=os.environ.get("S3_SECRET_ACCESS_KEY"),
        config=Config(s3={"addressing_style": "virtual"}, signature_version="v4"),
    )

    print("Start downloading")
    downloaded_path = download_file_from_s3(s3_client, "IMG_6376_2.mp4")
    print("Done downloading")
    
    print("Start converting to chunks")
    result_path = split_video(downloaded_path, 10)
    print("Finished chunking")
    
    print("Start uploading")
    upload_chunked_to_s3(s3_client, result_path)
    print("Finished uploading")

    print("exited")