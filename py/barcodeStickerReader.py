# Copyright 2023 Anish George V
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import sys
import os
import re
import cv2 as cv
import pytesseract
import argparse
import numpy as np
import logging
from logging.handlers import TimedRotatingFileHandler
from pytesseract import Output
from IPython.display import display
from pyzbar.pyzbar import decode
from PIL import Image
from pathlib import Path
from pdf2image import convert_from_path

#Remove Later
import matplotlib.pyplot as plt
SEARCH_PATTERN='[a-zA-Z0-9][A-Z][0-9]{8,9}[\/][0-9]{9,10}'
CASE_NO_PATTERN='[0-9]{9,10}$'
MIN_OCR_CONF=79
TEMPLATE_IMG='BarcodeTemplate.JPG'
SUCCESS_FOLDER='Passed'
FAILURE_FOLDER='Failed'
LOGGER=None
# Create a log
def create_timed_rotating_log():
    path='.//logs//renamePDFForms.log'
    logFormat='%(asctime)s - %(levelname)s - %(message)s'
    myLogger = logging.getLogger("RenamePDFForms")
    myLogger.setLevel(logging.DEBUG)
    #myLogger.__format__('%(asctime)s - %(message)s')
    handler = TimedRotatingFileHandler(path,
                                       when="d",
                                       interval=1,
                                       backupCount=10)
    formatter = logging.Formatter(logFormat)
    #formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    consoleHandler = logging.StreamHandler()
    bf = logging.Formatter(logFormat)
    handler.setFormatter(bf)
    myLogger.addHandler(handler)
    myLogger.addHandler(consoleHandler)
    return myLogger
#Perform OCR on sticker to extract text
#Check for confidence score and retrun filename wit MRN if confident.
def extractMRNFilename(stickerImage, baseFileName):
    delimiter='/'
    results = pytesseract.image_to_data(stickerImage, output_type=Output.DICT)
    #LOGGER.debug(len(results["text"]))
    for i in range(0, len(results["text"])) :
        # extract the OCR text itself along with the confidence of the text localization
        text = results["text"][i]
        text=text.replace('o','0')
        text=text.replace('O','0')
        matchedMsg=re.search(SEARCH_PATTERN,text)
        if delimiter in text and matchedMsg is None:
            LOGGER.info('%s does not match expected pattern. Hence ignoring',text)
        if matchedMsg is not None:
            conf = float(results["conf"][i])
            if conf>MIN_OCR_CONF :
                fileName = matchedMsg.group(0)
                fileName = re.search(CASE_NO_PATTERN,fileName).group(0)
                fileName = fileName.replace(delimiter,'_')
                LOGGER.info('Changing %s to %s with %s confidence',baseFileName,fileName,conf)
                return fileName
            LOGGER.info('OCR conf %s is less than %s for %s ',conf,MIN_OCR_CONF,matchedMsg.group(0))
    return None
#This method tries to locate a barcode from provided image as array
def extractBarcodeData(imageArr, baseFileName):
    # Decode the barcode image
    detectedBarcodes = decode(imageArr)
    # Initializing the fileName
    fileName=None
    # If not detected then print the message
    if not detectedBarcodes:
        #LOGGER.debug('Unable to detect barcode in %s',baseFileName)
        return None
    for barcode in detectedBarcodes: 
        # if identified item is a QR Code, then ignore
        if barcode.type == 'QRCODE' :
            continue
        # Expecting only one barcode hence taking the last added barcode
        barcddata=barcode.data
        # if identified barcode is empty then try for next
        if barcddata is None or barcddata == '' :
            continue
        fileName=str(barcddata, 'UTF-8')
        LOGGER.info('Changing %s to %s using barcode',baseFileName,fileName)
    return fileName
#Crop the image to the area containing sticker
def locateAndcropSticker(page1):
    imgarr=np.array(page1)
    page1Array=imgarr.copy()
    page1Array=cv.cvtColor(page1Array, cv.COLOR_BGR2RGB)
    template=cv.imread(TEMPLATE_IMG)
    template = cv.cvtColor(template, cv.COLOR_BGR2RGB)
    # Apply template Matching with the method
    res = cv.matchTemplate(page1Array,template,cv.TM_CCOEFF_NORMED)
    # Grab the Max and Min values, plus their locations
    min_val, max_val, min_loc, max_loc = cv.minMaxLoc(res)
    # For TM_CCOEFF_NORMED method, top left is max_loc
    top_left = max_loc
    # shape of template
    height, width,channels = template.shape
    # Assign the Bottom Right of the rectangle
    bottom_right = (top_left[0] + width*4, top_left[1] + height)
    #Cropping the full image to the barcode sticker
    barcodeSticker=page1Array[top_left[1]:bottom_right[1],top_left[0]:bottom_right[0]]
    return barcodeSticker
#Crop the image to the area containing sticker
def cropToStickerImg(page1):
    imgarr=np.asarray(page1)
    page1Array=imgarr.copy()
    h,w,c = page1Array.shape
    CROP_FROM_TOP = round(0.01*h)
    CROP_BOTTOM_FROM_TOP = round(0.18*h)
    CROP_LEFT_FROM_RGT = round(0.60*w)
    cropped=page1Array[CROP_FROM_TOP:CROP_BOTTOM_FROM_TOP, CROP_LEFT_FROM_RGT:w]
    return cropped
# process all the pdf forms in a folder
def processfolder(srcFolder, dstFolder,correlationId):
    LOGGER.info('%s Processing file : %s',correlationId, srcFolder)
    #os.chdir(srcFolder)
    baseFileName=''
    passCount=0
    failCount=0
    try:
        baseFileName=srcFolder
        file=baseFileName
        srcDirName=file.rsplit('\\',2)[1]
        LOGGER.info("%s SRC Dir : %s",correlationId, srcDirName)
        destFileName=None
        if ('.pdf' not in baseFileName):
            LOGGER.info("%s Ignoring filename : %s",correlationId, file)
            return
        #convert pdf to jpeg using pdf2image, taking only page 1
        #imgList=convert_from_path(file, fmt="jpeg", grayscale=True,last_page=1)
        #convert pdf to jpeg all pages, to look for barcode in all pages
        imgList=convert_from_path(file, fmt="jpeg", grayscale=True)
        loopCounter=0
        LOGGER.info("%s Working on filename : %s",correlationId, file)
        extractionMethod='BarCode'
        for page in imgList :
            loopCounter=loopCounter+1
            # Checking for a barcode in the entire page
            destFileName=extractBarcodeData(np.asarray(page),baseFileName+'-FullPage '+str(loopCounter))
            # If barcode reader could not extract from whole page trying to Locate Barcode
            if destFileName is None :
                #Locating Barcode sticker using tempate match TM_CCOEFF_NORMED
                stickerImageTempMatch=locateAndcropSticker(page)
                # First attempting read barcode sticker
                destFileName=extractBarcodeData(stickerImageTempMatch,baseFileName+'-TemplateMatch Page '+str(loopCounter))
                # If barcode reader could not extract trying to crop the top margin
                if destFileName is None :
                    topMargin=cropToStickerImg(page)
                    # First attempting with barcode reader
                    destFileName=extractBarcodeData(topMargin,baseFileName+'-Top Margin page '+str(loopCounter))
            if destFileName is not None :
                #Located File name, hence exiting loop
                #LOGGER.info('Exiting loop as name %s identified',destFileName)
                break
        # IF Extracting barcode data from all available pages failed. Trying with OCR
        if destFileName is None :
            #Locating sticker in page 1 of the pdf
            stickerImageTempMatch=locateAndcropSticker(imgList[0])
            destFileName=extractMRNFilename(stickerImageTempMatch,baseFileName)
            extractionMethod="Tesseract-OCR"
        if destFileName is None :
            LOGGER.warning('%s Failed to extract case no for %s',correlationId,baseFileName)
            failCount=failCount+1
            print(correlationId+"#OutputStatus : Failure for "+baseFileName)
            sys.exit(101)
        else :
            absDestFile=srcDirName+'_'+destFileName
            print(correlationId+"#OutputStatus : Success for "+baseFileName)
            print(correlationId+"#OutputPayLoad : "+destFileName)
            LOGGER.info("##Output:{%s,status:Success,extractionMethod:%s,extractedValue:%s}:Output##",correlationId,extractionMethod,destFileName)
            passCount=passCount+1
            return srcDirName+'_'+destFileName
    except Exception as e:
        LOGGER.error ('%sError for %s details %s',correlationId,file,e)
        failCount=failCount+1
        sys.exit(201)
    LOGGER.info('%s Completed Processing. Succeeded for %s and failed for %s files',correlationId,passCount,failCount)
# Main code 
# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--inputFile", required = True, help = "path to the folder containing pdf file")
ap.add_argument("-o", "--outputfolder", required = False, help = "output folder")
ap.add_argument("-t", "--templateimg", required = True, help = "Path to barcode template image")
ap.add_argument("-c", "--minOCRConf", required = False, help = "Minimum OCR Confidence. Default to 79")
ap.add_argument("-r", "--correlationID", required = True, help = "Correlation ID for the transaction")
args = vars(ap.parse_args())
LOGGER=create_timed_rotating_log()
sourceFile=args["inputFile"]
destFolder = args["outputfolder"]
correlationId=args["correlationID"]
TEMPLATE_IMG = args["templateimg"]
ocrConf=args["minOCRConf"]
if ocrConf is not None:
    MIN_OCR_CONF = float(ocrConf)
#print("Processing folder : " + sourceFile)
processfolder(sourceFile, destFolder,correlationId)
LOGGER.info("Completed Processing")
sys.exit(0)