import argparse
import csv
import qscript

def parse_args():
    parser = argparse.ArgumentParser(
        description="Record a browser video for every row of input.csv; "
                    "optionally upload each video to the server and preview it."
    )
    parser.add_argument(
        "--server",
        metavar="URL",
        help="video service URL, e.g. http://127.0.0.1:8000. "
             "If set, each recorded video is uploaded and opened in Chromium.",
    )
    parser.add_argument(
        "--view-seconds",
        type=float,
        default=10,
        metavar="N",
        help="how long to show each preview: N > 0 keeps the browser open N seconds, "
             "0 keeps it open until you press Enter (default: 10)",
    )
    args = parser.parse_args()
    if args.view_seconds < 0:
        parser.error("--view-seconds must be 0 or greater")
    return args


def preview(url, view_seconds):
    """Open the uploaded video in Chromium's built-in player."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        try:
            page = browser.new_page()
            page.goto(url)
            if view_seconds > 0:
                try:
                    page.wait_for_event("close", timeout=view_seconds * 1000)
                except Exception:
                    pass
            else:
                input("Previewing {} - press Enter to continue...".format(url))
        finally:
            browser.close()


def main():
    args = parse_args()

    upload_video = None
    if args.server:
        from video_client import UploadVideo as upload_video

    qscript.PATH_TO_VIDEO_FOLDER = "./video"

    with open("input.csv", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";", quotechar='"'):
            company_name = row["Company Name"]
            path = qscript.CaptureVideo_Magento(
                row["URL"], company_name, row["Language"], row["Country"],
                row["Postcode"], row["City"], row["Street"], row["HouseNo"],
            )

            if not path:
                print("FAILED: {}".format(company_name))
                continue
            print(path)

            if upload_video is None:
                continue

            try:
                url = upload_video(args.server, path, company_name)
            except Exception as e:
                print("UPLOAD FAILED: {}: {}".format(company_name, e))
                continue
            print("Uploaded: {}".format(url))

            try:
                preview(url, args.view_seconds)
            except Exception as e:
                print("PREVIEW FAILED: {}: {}".format(company_name, e))


if __name__ == "__main__":
    main()
