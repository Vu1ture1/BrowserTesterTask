# CSV-driven Browser Automation Video Recorder

Records a video of automated browser actions for every row of an input CSV file, using Python and Playwright (sync API, Chromium). While recording, **zoom events** can be marked (F5 or `window.__zoomAt(x, y)`). The video service then renders them into a copy with a Camtasia-style zoom: a smooth zoom-in → hold → zoom-out around the mouse position.

For each row the script:
1. opens DuckDuckGo;
2. glides a visible cursor to the search box and zooms in on it;
3. types `Magento developer in <City>` character by character, then zooms out;
4. clicks the search button;
5. zooms in on the first result, zooms out and clicks it.

The recording is saved as `video/<Company Name>.webm`, and the zoom events as `video/<Company Name>.zoom.json`.

The video service (upload, storage, zoom post-processing in Docker) is in [BrowserTesterTaskServerDocker](https://github.com/Vu1ture1/BrowserTesterTaskServerDocker).

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

Run the scripts with the virtual environment active (the prompt shows `(.venv)`). Otherwise Python fails with `No module named 'playwright'`.

## Usage

```bash
python capture_video.py
```

The script processes every row of `input.csv` and prints the path of each saved video, or `FAILED: <Company Name>` if a row could not be recorded:

```
C:\BrowserTesterTask\video\Acme GmbH.webm
C:\BrowserTesterTask\video\Beta Ltd.webm
```

### Upload and preview

With `--server`, each recorded video is also uploaded to the video service and opened in Chromium's built-in player. Start the service first with `docker compose up -d --build` (see the [server's README](https://github.com/Vu1ture1/BrowserTesterTaskServerDocker)).

```bash
python capture_video.py --server http://127.0.0.1:8000 --view-seconds 10
```

```
C:\BrowserTesterTask\video\Acme GmbH.webm
Uploaded: http://127.0.0.1:8000/media/Acme_GmbH.webm
Zoomed: http://127.0.0.1:8000/media/zoomed/Acme_GmbH.webm
```

If the recording has zoom events, its `.zoom.json` is uploaded with it. The script then waits until the server has rendered the zoomed copy and previews that copy instead of the original.

| Option | Meaning |
|---|---|
| `--server URL` | Upload each recorded video to this service and preview it. Without it, videos are only recorded. |
| `--view-seconds N` | How long each preview stays open: `N > 0` closes the browser after N seconds, `0` waits until you press Enter. Default: `10`. |

If an upload, zoom processing or preview fails, the script prints `UPLOAD FAILED: ...`, `ZOOM FAILED: ...` or `PREVIEW FAILED: ...` and continues with the next row. `requests` is imported only when `--server` is used, so plain recording works without it.

## Zoom events

Zoom is a **post effect**. The browser records the normal full-size video, and only the zoom points are written down; the server (or `apply_zoom.py`) renders the zoom afterwards.

### Marking a zoom

- **F5** in the recorded browser window toggles the zoom at the current mouse position: the first press marks the start of the zoom-in, the second the start of the zoom-out. The page is **not** reloaded.
- **`window.__zoomAt(x, y)`** does the same toggle from the automation scenario (automation does not press F5). In Python: `zoom_at_cursor(page)` calls it at the scripted cursor position.
- An on-screen indicator shows the state:
  - zoom-in: a green ring closes in on the point, and the cursor keeps a green outline while zoomed;
  - zoom-out: a red ring expands.

The zoom state is kept in Python (`context.expose_binding`), so it survives navigation. For example, the first F5 on the results page and the second on the opened site form one pair.

### Sidecar file

When at least one event was marked, `video/<Company Name>.zoom.json` is written next to the video. Without events no file is written, and a stale one from a previous recording is removed.

```json
{
  "viewport": {"width": 1280, "height": 720},
  "fps": 25,
  "zoom_factor": 2.0,
  "ramp_sec": 0.5,
  "events": [
    {"t": 2.32, "x": 538.5, "y": 59.0, "type": "in"},
    {"t": 6.96, "x": 538.5, "y": 59.0, "type": "out"}
  ]
}
```

- **`x`, `y`**: mouse position in viewport pixels. The recording uses `record_video_size == viewport` (1280×720), so they are also video pixels.
- **`t`**: seconds since the video start. Playwright starts a page's video at its first painted frame, which comes 0.1–0.5 s after the context is created (longer with a visible window). The clock therefore starts right after `new_page()`, once the browser has painted a frame (`requestAnimationFrame`). Measured offset between an event and the video: ≤ 3 frames (0.12 s).
- **`zoom_factor`, `ramp_sec`**: set in `ZOOM_SETTINGS` in `qscript.py`.

### Rendering locally

`apply_zoom.py` is in the server repository. It can render a sidecar without Docker if ffmpeg is installed:

```bash
python path/to/apply_zoom.py --video "video/Acme GmbH.webm"            # -> video/Acme GmbH.zoomed.webm
python path/to/apply_zoom.py --video "video/Acme GmbH.webm" --dry-run  # print the ffmpeg command only
```

## Input format

UTF-8 (with or without BOM), delimiter `;`, field qualifier `"`, with this header row:

```
URL;Company Name;Language;Country;Postcode;City;Street;HouseNo
```

`URL` is the page to open, `City` is used in the search query and `Company Name` becomes the video file name. The other columns are passed to the function as required by its signature but are not used by the sample scenario.

## Upload client

`video_client.py` talks to the video upload web service.

```python
from video_client import UploadVideo, GetVideoURL, WaitForZoomedVideo

UploadVideo("http://127.0.0.1:8000", r"video\Acme GmbH.webm", "ACME GmbH")
# 'http://127.0.0.1:8000/media/ACME_GmbH.webm'

GetVideoURL("http://127.0.0.1:8000", "ACME GmbH")
# 'http://127.0.0.1:8000/media/ACME_GmbH.webm'

WaitForZoomedVideo("http://127.0.0.1:8000", "ACME GmbH")
# 'http://127.0.0.1:8000/media/zoomed/ACME_GmbH.webm'
```

- **`UploadVideo`** returns the URL of the original video. If `<video>.zoom.json` exists next to the video, it is uploaded too, and the server renders a zoomed copy in the background.
- **`GetVideoURL`** returns the URL of the original video.
- **`WaitForZoomedVideo`** polls the server until the zoomed copy is ready and returns its URL. It returns `None` if the video was uploaded without zoom events. It raises `VideoServiceError` if processing failed or did not finish within `timeout` seconds (default 300).

If the server answers with an error, the functions raise `VideoServiceError` with the HTTP status and the server's message, for example `HTTP 404 ... Company 'Nope' not found.` If the server cannot be reached, `requests` raises `ConnectionError`.

The same calls are available from the command line for a quick manual check:

```bash
python video_client.py upload http://127.0.0.1:8000 "video/Acme GmbH.webm" "ACME GmbH"
python video_client.py get    http://127.0.0.1:8000 "ACME GmbH"
```