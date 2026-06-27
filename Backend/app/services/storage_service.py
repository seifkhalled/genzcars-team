import logging
from supabase import Client
from typing import List, Optional

logger = logging.getLogger(__name__)


def upload_file(
    supabase: Client,
    bucket: str,
    path: str,
    file_bytes: bytes,
    content_type: str,
) -> Optional[str]:
    try:
        supabase.storage.from_(bucket).upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": content_type, "upsert": "true"},
        )
        public_url = supabase.storage.from_(bucket).get_public_url(path)
        return public_url
    except Exception as e:
        logger.warning("Failed to upload %s to Supabase: %s", path, e)
        return None


def delete_file(supabase: Client, bucket: str, path: str) -> None:
    supabase.storage.from_(bucket).remove([path])


def delete_files(supabase: Client, bucket: str, paths: List[str]) -> None:
    if paths:
        supabase.storage.from_(bucket).remove(paths)
