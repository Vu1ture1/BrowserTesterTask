import mimetypes
import os
import sys

import requests

TIMEOUT = (10, 300)

class VideoServiceError(Exception):
    """The server answered with an error (4xx/5xx) or an unexpected response."""


def _endpoint(server_url, path):
    return server_url.rstrip("/") + path


def _video_url_from(response):
    """Return video_url from a successful JSON response, or raise VideoServiceError."""
    if not response.ok:
        try:
            message = response.json().get("error") or response.text
        except ValueError:
            message = response.text
        raise VideoServiceError(
            "HTTP {} from {}: {}".format(response.status_code, response.url, message.strip())
        )

    try:
        return response.json()["video_url"]
    except (ValueError, KeyError, TypeError):
        raise VideoServiceError(
            "Unexpected response from {}: {}".format(response.url, response.text[:200])
        )


def UploadVideo(server_url: str, video_path: str, company_name: str) -> str:
    """Uploads a video file to the server and returns its URL."""
    filename = os.path.basename(video_path)
    content_type = mimetypes.guess_type(filename)[0] or "video/webm"

    with open(video_path, "rb") as f:
        response = requests.post(
            _endpoint(server_url, "/upload"),
            files={"file": (filename, f, content_type)},
            data={"company_name": company_name},
            timeout=TIMEOUT,
        )
    return _video_url_from(response)


def GetVideoURL(server_url: str, company_name: str) -> str:
    """Returns the video URL for the given company name."""
    response = requests.get(
        _endpoint(server_url, "/get_video_url"),
        params={"company_name": company_name},
        timeout=TIMEOUT,
    )
    return _video_url_from(response)


def _main(argv):
    usage = (
        "usage:\n"
        "  python video_client.py upload <server_url> <video_path> <company_name>\n"
        "  python video_client.py get    <server_url> <company_name>"
    )
    try:
        if len(argv) == 5 and argv[1] == "upload":
            print(UploadVideo(argv[2], argv[3], argv[4]))
        elif len(argv) == 4 and argv[1] == "get":
            print(GetVideoURL(argv[2], argv[3]))
        else:
            print(usage, file=sys.stderr)
            return 2
    except (VideoServiceError, requests.RequestException, OSError) as e:
        print("Error: {}".format(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
