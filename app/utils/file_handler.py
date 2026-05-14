# app/utils/file_handler.py

import os
from fastapi import UploadFile

UPLOAD_DIR = "uploads"


def save_upload_file(file: UploadFile) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as f:
        f.write(file.file.read())

    return file_path
