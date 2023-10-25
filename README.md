# barcodelocator
This script can be used to locate a barcode sticker and read the barcode from a PDF with multiple pages. This script uses basic computer vision to locate an image (a barcode sticker) in a scanned pdf. Once it is able to locate the image, it reads the barcode value and returns. 

Sample Usecase:
We had a bunch of scanned multi page pdf documents which were manually renamed and uploaded into another system. This script is used as part of another program to automate that entire process. Using both we were able to achieve 80% automation. There were still another 20% where due to poor resolution manual activity is still there.

#Pre Requisites
Install the below
1. Python (3.10)
2. poppler-23.01.0
3. Tesseract-OCR
Further use pip install for below libraries
1. pdf2image
2. opencv-python
3. pyzbar
4. pathlib 
5. argparse 
6. IPython
7. matplotlib
