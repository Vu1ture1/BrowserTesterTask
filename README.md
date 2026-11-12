# CSV-driven Browser Automation Video Recorder

Records a video of automated browser actions for every row of an input CSV file, using Python and Playwright (sync API, Chromium).

For each row the script opens DuckDuckGo, glides a visible cursor to the search box, types `Magento developer in <City>` character by character, clicks the search button, waits for the results and clicks the first one. The recording is saved as `video/<Company Name>.webm`.

## Requirements

- Python 3.9 or newer (tested on 3.9.13 and 3.14.7)
- Chromium installed by Playwright

## Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m playwright install chromium
```

## Usage

```bash
python capture_video.py
```

The script processes every row of `input.csv` and prints the path of each saved video, or `FAILED: <Company Name>` if a row could not be recorded:

```
C:\BrowserTesterTask\video\Acme GmbH.webm
C:\BrowserTesterTask\video\Beta Ltd.webm
C:\BrowserTesterTask\video\Gamma SRL.webm
```

### Upload and preview

With `--server`, each recorded video is also uploaded to the video upload web service and opened in Chromium's built-in player. Start the service first with `dotnet run` (see the server's README).

```bash
python capture_video.py --server http://127.0.0.1:8000 --view-seconds 10
```

```
C:\BrowserTesterTask\video\Acme GmbH.webm
Uploaded: http://127.0.0.1:8000/media/Acme_GmbH.webm
C:\BrowserTesterTask\video\Beta Ltd.webm
Uploaded: http://127.0.0.1:8000/media/Beta_Ltd.webm
```

| Option | Meaning |
|---|---|
| `--server URL` | Upload each recorded video to this service and preview it. Without it, videos are only recorded. |
| `--view-seconds N` | How long each preview stays open: `N > 0` closes the browser after N seconds, `0` waits until you press Enter. Default: `10`. |

If an upload or preview fails, the script prints `UPLOAD FAILED: ...` or `PREVIEW FAILED: ...` and continues with the next row. `requests` is imported only when `--server` is used, so plain recording works without it.

## Input format

UTF-8 (with or without BOM), delimiter `;`, field qualifier `"`, with this header row:

```
URL;Company Name;Language;Country;Postcode;City;Street;HouseNo
```

`URL` is the page to open, `City` is used in the search query and `Company Name` becomes the video file name. The other columns are passed to the function as required by its signature but are not used by the sample scenario.

## Upload client

`video_client.py` talks to the video upload web service (see the server's README - https://github.com/Vu1ture1/BrowserTesterTaskServer). Start the service first with `dotnet run`.

```python
from video_client import UploadVideo, GetVideoURL

UploadVideo("http://127.0.0.1:8000", r"video\Acme GmbH.webm", "ACME GmbH")
# 'http://127.0.0.1:8000/media/ACME_GmbH.webm'

GetVideoURL("http://127.0.0.1:8000", "ACME GmbH")
# 'http://127.0.0.1:8000/media/ACME_GmbH.webm'
```

Both functions return the video URL. If the server answers with an error, they raise `VideoServiceError` with the HTTP status and the server's message, for example `HTTP 404 ... Company 'Nope' not found.`; if the server cannot be reached, `requests` raises `ConnectionError`.

The same calls are available from the command line for a quick manual check:

```bash
python video_client.py upload http://127.0.0.1:8000 "video/Acme GmbH.webm" "ACME GmbH"
python video_client.py get    http://127.0.0.1:8000 "ACME GmbH"
```
