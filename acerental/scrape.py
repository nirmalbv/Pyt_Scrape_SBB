from selenium.webdriver import Chrome
from selenium.webdriver import ChromeOptions
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
import time
import json
import pandas as pd
from flask import Flask, jsonify
import datetime
import re
ACE_URL = 'https://www.acerentalcars.co.nz/'
app = Flask(__name__)

class ACE():
    def __init__(self):
        options = ChromeOptions()
        #options.add_argument("--headless")
        options.add_argument('--disable-logging')
        #options.add_argument("--start-maximized")
        #options.add_argument("--no-sandbox")
        self.browser = Chrome(executable_path='/home/mancunian92/Documents/chromedriver', chrome_options=options)
        self.browser.get(ACE_URL)
        self.searchResults = []
        self.dropDownOptions = []
        time.sleep(2)
        self.getDropDownOptions()    
    
    def getDropDownOptions(self):
        self.formOptions = self.browser.find_element_by_name("formPickupLocation")
        self.dropDownOptions = [o.text for o in Select(self.browser.find_element_by_name("formPickupLocation")).options]
        print(self.dropDownOptions)
 
    def pushDateToBrowser(self, date, diffMonths, isDropOff=False):
        if isDropOff:
            self.browser.find_element_by_id("inline_Dropoff_Date_1").click()
            while(diffMonths > 0):
                self.browser.find_elements_by_class_name("l-form-b__field--datetime")[1].find_element_by_class_name("pika-next").click()
                diffMonths-=1
            tableElem = self.browser.find_elements_by_class_name("l-form-b__field--datetime")[1].find_element_by_class_name("pika-lendar").find_element_by_xpath("./table/tbody")
        else:
            self.browser.find_element_by_id("inline_Pickup_Date_1").click()
            while(diffMonths > 0):
                self.browser.find_elements_by_class_name("l-form-b__field--datetime")[0].find_element_by_class_name("pika-next").click()
                diffMonths-=1
            tableElem = self.browser.find_elements_by_class_name("l-form-b__field--datetime")[0].find_element_by_class_name("pika-lendar").find_element_by_xpath("./table/tbody")
        expr = "./tr/td[@data-day="+ str(date.day) + "]/button"
        tableElem.find_element_by_xpath(expr).click()
    
    def pushTimeToBrowser(self, time, isDropoff = False):
        if isDropoff:
            Select(self.browser.find_element_by_name("formDropoffTime")).select_by_value(time)
        else:
            Select(self.browser.find_element_by_name("formPickupTime")).select_by_value(time)

    def selectDates(self, pickupDateInString, dropOffDateInString, pickupTime, dropOffTime):
        currDate = datetime.datetime.now()
        pickupDate = datetime.datetime.strptime(pickupDateInString, '%d/%b/%Y')
        dropoffDate = datetime.datetime.strptime(dropOffDateInString, '%d/%b/%Y')
        diffMonthsPickup = (pickupDate.year - currDate.year) * 12 + (pickupDate.month - currDate.month)
        diffMonthsDropoff = (dropoffDate.year - pickupDate.year) * 12 + (dropoffDate.month - pickupDate.month)
        self.pushDateToBrowser(pickupDate, diffMonthsPickup)
        self.pushDateToBrowser(dropoffDate, diffMonthsDropoff, isDropOff=True)
        self.pushTimeToBrowser(pickupTime)
        self.pushTimeToBrowser(dropOffTime, isDropoff=True)
     
    def selectLocation(self, pickupLocation, dropOffLocation, isSamePickup = True):
        # First, select the pick up location.
        pickupIndex = self.dropDownOptions.index(pickupLocation)
        Select(self.formOptions).select_by_index(pickupIndex)
        if isSamePickup != True:
            dropOffElem = Select(self.browser.find_element_by_name("formDropoffLocation"))
            dropOffOptions = [o.text for o in dropOffElem.options]
            dropOffIndex = dropOffOptions.index(dropOffLocation)
            dropOffElem.select_by_index(dropOffIndex)
    
    def enterPromocode(self, promoCode):
        self.browser.find_element_by_name("formPromoCode").send_keys(promoCode)

    def search(self, searchRequest):
        pickupDate = searchRequest["pickupDate"]
        dropoffDate = searchRequest["dropDate"]
        pickupLocation = searchRequest["pickupPoint"]
        dropoffLocation = searchRequest["dropPoint"]
        pickupTime = searchRequest["pickupTime"]
        dropoffTime = searchRequest["dropTime"]
        self.selectDates(pickupDate, dropoffDate, pickupTime, dropoffTime)
        self.selectLocation(pickupLocation, dropoffLocation, isSamePickup=False)
        self.browser.find_element_by_class_name("l-hero__booking-action__submit--btn").click()
    
    def parseCars(self, cars):
        try:
            parsedCars = []
            cars = cars.find_elements_by_class_name("c-vehicle-card")
            totalCars = len(cars)
            parsedCar = {
                    "carName": "",
                    "carType": "",
                    "gearType": "",
                    "maxSeats": "",
                    "maxLuggage": "",
                    "image": "",
                    "gpsIncluded": True,
                    "gpsCost": "",
                    "insuranceType": "",
                    "insuranceCost": "",
                    "carCost": "",
                    "totalCost": "",
                    "currencyCode": ""
                }
            for i in range(0,totalCars):
                action = ActionChains(self.browser)
                detailsButton = self.browser.find_elements_by_class_name("c-vehicle-card")[i].find_element_by_class_name("c-vehicle-card__action")
                print(detailsButton.text)
                #time.sleep(4)
                action.move_to_element(detailsButton)
                action.click(detailsButton).perform()
                carDetailsDOM = WebDriverWait(self.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-vehicle-panel__inner"))
                parsedCar = self.parseCarDetail(carDetailsDOM, parsedCar)   
                parsedCars.append(parsedCar)
                self.browser.back()
                WebDriverWait(self.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-cars__cards"))
            return parsedCars
        except TimeoutException:
                pass
        
    
    def parseCarDetail(self, carDetail, parsedCar):
        return parsedCar

        
        

@app.route("/")
def home():
    return "Scraper Service API"

@app.route("/getPickupLocations")
def getPickupLocations():
    ace = ACE()
    return jsonify({"locations": ace.dropDownOptions})

if __name__ == "__main__":
    #app.run(debug=True)
    MAX_TIMEOUT = 10
    ace = ACE()
    #ace.enterPromocode("HELLO")
    ace.search({"pickupPoint": "Perth", "dropPoint": "Sydney", "pickupDate": "20/May/2019", "dropDate": "25/May/2019", "pickupTime": "09:00:00", "dropTime": "15:00:00"})
    try:
        carsDOM = WebDriverWait(ace.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-cars__cards"))
        parsed = ace.parseCars(carsDOM)
        print(parsed)
    except TimeoutException:
        print("Loading took too much time!-Try again")


    