import os
from PIL import Image

# note: these are MY directories. these will need to be set in the GUI
RAW_PATH = "C:/Games/Steam/steamapps/common/Skyrim Special Edition/screenshots"
EDIT_PATH = "C:/Users/vegap/Videos/The Elder Scrolls V  Skyrim Special Edition"

# if you want to delete the originals
deleteOriginals = False

def main():
    os.chdir(RAW_PATH)
    for file in os.listdir():
        rawFilename = file.strip(".bmp")
        newFilename = f"{rawFilename}.png"
        img = Image.open(file)
        img.save(f"{EDIT_PATH}/{newFilename}")
        img.close()
        if deleteOriginals == True:
            os.remove(file)

if __name__ == "__main__":
    main()