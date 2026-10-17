import os
from minio import Minio

def download_file():
    # MinIO credentials from docker exec output
    # Since we are running outside the docker network, we use localhost:9000
    client = Minio(
        "localhost:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False
    )
    
    # Based on main.py line 1373: client.put_object("filled-forms", object_name, ...)
    bucket = "filled-forms"
    # Based on main.py line 1370: object_name = f"{household_hash}/filled_forms/{scheme_part}_complete.pdf"
    object_name = "1d0d99f65d941c9dda7f5d80af5473e8c7440356de05a798548cc4fca94ed997/filled_forms/nsapignoaps_complete.pdf"
    destination_file = "verification_filled_form.pdf"
    
    try:
        print(f"Downloading {object_name} from bucket '{bucket}'...")
        client.fget_object(bucket, object_name, destination_file)
        print(f"Successfully downloaded to {destination_file}")
    except Exception as e:
        print(f"Error downloading file: {e}")

if __name__ == "__main__":
    download_file()
