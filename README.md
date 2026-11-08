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

## Input format

UTF-8, delimiter `;`, field qualifier `"`, with this header row:

```
URL;Company Name;Language;Country;Postcode;City;Street;HouseNo
```

`URL` is the page to open, `City` is used in the search query and `Company Name` becomes the video file name. The other columns are passed to the function as required by its signature but are not used by the sample scenario.