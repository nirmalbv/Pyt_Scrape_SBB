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
from flask import request
from multiprocessing import Pool
import copy
from itertools import repeat

MAX_TIMEOUT = 12
ACE_URL = 'https://www.acerentalcars.co.nz/'
app = Flask(__name__)


def parseCarsParallel(ace):
        try:
            parsedCars = []
            cars = WebDriverWait(ace.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-cars__cards"))
            cars = cars.find_elements_by_class_name("c-vehicle-card")
            totalCars = len(cars)
            req = ace.request
            with Pool() as pool:
                parsedCars = pool.starmap(parseParallelHelper, zip(range(1, totalCars), repeat(req)))
            return parsedCars
        except TimeoutException:
            print("Am i here in time out exception??")
            return parsedCars

def parseParallelHelper(index, request):
        ace = ACE()
        ace.search(request)
        WebDriverWait(ace.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-cars__cards"))
        parsedCar = {
                    "carName": "",
                    "carType": "",
                    "gearType": "",
                    "maxSeats": "",
                    "maxLuggage": "",
                    "image": "",
                    "carCost": "",
                    "totalCost": "",
                    "currencyCode": "",
                    "insuranceDetails": [],
                    "otherOptions": []
                }
        itemSummary = ace.browser.find_element_by_class_name("l-booking-summary-bar")
        ace.browser.execute_script("arguments[0].style.visibility='hidden'", itemSummary)
        action = ActionChains(ace.browser)
        detailsButton = ace.browser.find_elements_by_class_name("c-vehicle-card")[index].find_element_by_class_name("c-vehicle-card__action")
        action.move_to_element(detailsButton)
        action.click(detailsButton).perform()
        WebDriverWait(ace.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-booking__step"))
        parsedCar = parseCarDetailParallel(ace.browser, parsedCar)
        return parsedCar

def parseCarDetailParallel(browser, parsedCar):
        elements = browser.find_elements_by_class_name("l-booking__step")
        inner = browser.find_element_by_class_name("l-vehicle-panel__inner")
        insuranceDetails = elements[0].find_elements_by_class_name("c-option-card__main")
        otherOptions = elements[1].find_elements_by_class_name("x-option-card__main")
        parsedCar["carName"] = inner.find_element_by_class_name("l-vehicle-panel__subtitle").get_attribute("textContent")
        parsedCar["carType"] = inner.find_element_by_class_name("l-vehicle-panel__title").get_attribute("textContent")
        parsedCar["image"] = inner.find_element_by_class_name("l-vehicle-panel__image").find_element_by_xpath('./img').get_attribute("src")


        specifications = inner.find_element_by_class_name("l-vehicle-panel__specifications")
        parsedCar["gearType"] = specifications.find_element_by_xpath('//img[contains(@src, "transmission")]').get_attribute("alt")
        parsedCar["maxSeats"] = specifications.find_element_by_xpath('//img[contains(@src, "passengers")]').get_attribute("alt")
        parsedCar["maxLuggage"] = specifications.find_element_by_xpath('//img[contains(@src, "luggage")]').get_attribute("alt")

        cost = WebDriverWait(browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-vehicle-panel__total"))
        parsedCar["carCost"] = cost.find_element_by_class_name("l-vehicle-panel__total-item-total").get_attribute("textContent")
        totalcost = cost.find_element_by_class_name("l-vehicle-panel__total-price")
        parsedCar["currencyCode"] = totalcost.find_element_by_xpath('./span').get_attribute("textContent")
        parsedCar["totalCost"] = totalcost.get_attribute("textContent")
        for _ins in insuranceDetails:
            insur = {
                "name": _ins.find_element_by_class_name("c-option-card__title").get_attribute("textContent"),
                "price": _ins.find_element_by_class_name("c-option-card__price").get_attribute("textContent")
            }
            parsedCar["insuranceDetails"].append(insur)

        for _opt in otherOptions:
            opt = {
                "title": _opt.find_element_by_class_name("x-option-card__title").get_attribute("textContent"),
                "price": _opt.find_element_by_class_name("x-option-card__price").get_attribute("textContent")
            }
            parsedCar["otherOptions"].append(opt)

        return parsedCar


class ACE():
    def __init__(self):
        options = ChromeOptions()
        options.add_argument("--headless")
        options.add_argument('--disable-logging')
        options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        options.add_argument('disable-gpu');
        options.add_argument('window-size=1200,1100');

        self.browser = Chrome(executable_path='drivers/chromedriver', options=options)
        self.browser.implicitly_wait(15)
        self.browser.get(ACE_URL)
        self.searchResults = []
        self.dropDownOptions = []
        self.request = {}
        time.sleep(2)
        self.getDropDownOptions()

    def getDropDownOptions(self):
        self.formOptions = self.browser.find_element_by_name("formPickupLocation")
        self.dropDownOptions = [o.text for o in Select(self.browser.find_element_by_name("formPickupLocation")).options]

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
        self.browser.find_element_by_xpath("//span[@class='l-hero__booking-action__submit--btn-text']").click()


    def parseCars(self, ace):
        try:
            parsedCars = []
            cars = WebDriverWait(self.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-cars__cards"))
            cars = cars.find_elements_by_class_name("c-vehicle-card")

            #Adding +1 to the totalCars because we are starting the index from 1
            totalCars = len(cars)+1
            # print (totalCars)
            for i in range(1,totalCars):
                parsedCar = {
                    "carName": "",
                    "carType": "",
                    "carCost": "",
                    "currencyCode": ""
                }
                # Hide the itineray summary
                itemSummary = self.browser.find_element_by_class_name("l-booking-summary-bar")
                self.browser.execute_script("arguments[0].style.visibility='hidden'", itemSummary)

                # To validate and exclude "Sold Out" cars
                # detailsButtonExist = len(self.browser.find_elements_by_xpath("(//*[contains(@class,'c-vehicle-card__action')])"+str([i])))
                # if detailsButtonExist > 0:

                # To Identify the particular Car card based on index (i)
                car = self.browser.find_element_by_xpath("(//div[@class='l-cars__cards']/div)"+str([i]))

                #To identify carName for a particular car
                parsedCar["carName"] = car.find_element_by_class_name("c-vehicle-card__subtitle").get_attribute("textContent")

                #To identify carType for a particular car
                parsedCar["carType"] = car.find_element_by_class_name("c-vehicle-card__title").get_attribute("textContent")

                #To identify image for a particular car
                # parsedCar["image"] = car.find_element_by_class_name("c-vehicle-card__image").find_element_by_xpath('./img').get_attribute("src")


                #To identify the specifications of a particular car like gearType, maxSeats, maxLuggage
                '''
                specifications = car.find_element_by_xpath("(//ul[contains(@class,'c-vehicle-card__specifications details')])"+str([i]))
                print ("(//ul[contains(@class,'c-vehicle-card__specifications details')])"+str([i]))

                #First way
                parsedCar["gearType"] = specifications.find_element_by_xpath("//img[contains(@src, 'transmission')]/preceding::li"+str([i])).text                        parsedCar["maxSeats"] = specifications.find_element_by_xpath("//img[contains(@src, 'passengers')]/..").text
                parsedCar["maxLuggage"] = specifications.find_element_by_xpath("//img[contains(@src, 'luggage')]/..").text

                #Second way
                parsedCar["gearType"] = specifications.find_element_by_xpath("//img[contains(@src, 'transmission')]/..").get_attribute("textContent")
                parsedCar["maxSeats"] = specifications.find_element_by_xpath("//img[contains(@src, 'passengers')]").get_attribute("textContent")
                parsedCar["maxLuggage"] = specifications.find_element_by_xpath("//img[contains(@src, 'luggage')]").get_attribute("textContent")
                '''

                #To identify carCost for a particular car
                parsedCar["carCost"] = self.browser.find_element_by_xpath("(//*[@class='c-vehicle-card__price'])"+str([i])).get_attribute("textContent")

                #To identify currencyCode for a particular car
                parsedCar["currencyCode"] = self.browser.find_element_by_xpath("(//*[@class='c-vehicle-card__price']/span)"+str([i])).get_attribute("textContent")

                #Appending to the json file for each car
                parsedCars.append(parsedCar)

            return parsedCars
        except TimeoutException:
            print("Am i here in time out exception??")
            return parsedCars


    def tearDown(self):
        self.browser.quit()


@app.route("/")
def home():
    return "Scraper Service API"

@app.route("/getPickupLocations")
def getPickupLocations():
    ace = ACE()
    return jsonify({"locations": ace.dropDownOptions})

@app.route("/acepricecrapping", methods={'POST'})
def search():
    req = request.get_json()
    ace = ACE()
    ace.search(req)
    if request.args.get("parallel") == "true":
        print("In parallel")
        ace.request = req
        parsed = parseCarsParallel(ace)
    else:
        parsed = ace.parseCars(ace)
        ace.tearDown()
    #To parse with "Parsed" object at the begining of Json response
    # return jsonify({"parsed": parsed})

    #To parse without "Parsed" object at the begining of Json response
    return jsonify(parsed)

if __name__ == "__main__":
    app.run(debug=True)
     # ace = ACE()
     # ace.enterPromocode("HELLO")
     # ace.search({"pickupPoint": "Perth", "dropPoint": "Sydney", "pickupDate": "20/May/2019", "dropDate": "25/May/2019", "pickupTime": "09:00:00", "dropTime": "15:00:00"})
     # try:
     #     carsDOM = WebDriverWait(ace.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-cars__cards"))
     #     parsed = ace.parseCars(carsDOM)
     #     print("Parsed is ", parsed)
     # except TimeoutException:
     #     print("Loading took too much time!-Try again")
