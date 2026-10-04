"""Organization options shared by the core, storage and Web API."""

CATEGORIES = {
    "画像": "jpg jpeg png gif bmp webp tif tiff heic svg ico avif raw",
    "動画": "mp4 mov avi mkv wmv webm m4v mpg mpeg",
    "音声": "mp3 wav flac aac ogg m4a wma opus",
    "文書": "pdf txt doc docx xls xlsx ppt pptx csv md rtf odt ods odp",
    "圧縮ファイル": "zip rar 7z tar gz bz2 xz",
}


def normalize_options(rule="extension", excluded_extensions=None):
    if rule not in ("extension", "type"):
        raise ValueError("整理ルールは extension または type を選んでください。")
    if excluded_extensions is None:
        excluded_extensions = []
    if not isinstance(excluded_extensions, list):
        raise ValueError("除外拡張子は一覧で指定してください。")
    normalized = set()
    for value in excluded_extensions:
        if not isinstance(value, str):
            raise ValueError("除外拡張子は文字列で指定してください。")
        value = value.strip().lower().lstrip(".")
        if not value or not value.isalnum():
            raise ValueError("除外拡張子には .exe のような拡張子を指定してください。")
        normalized.add("." + value)
    return {"rule": rule, "excluded_extensions": sorted(normalized)}


def destination_category(extension):
    return next((name for name, extensions in CATEGORIES.items()
                 if extension.lstrip(".") in extensions.split()), "その他")
