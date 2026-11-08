import csv
import qscript

def main():
    qscript.PATH_TO_VIDEO_FOLDER = "./video"
    
    with open("input.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter=";", quotechar='"'):
            path = qscript.CaptureVideo_Magento(
                row["URL"], row["Company Name"], row["Language"], row["Country"],
                row["Postcode"], row["City"], row["Street"], row["HouseNo"],
            )
            
            print(path if path else f"FAILED: {row['Company Name']}")

if __name__ == "__main__":
    main()
