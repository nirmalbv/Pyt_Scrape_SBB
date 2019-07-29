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
from collections import defaultdict

MAX_TIMEOUT = 40
ACE_URL = 'https://www.acerentalcars.co.nz/'
app = Flask(__name__)


class ACE():
    def __init__(self):
        options = ChromeOptions()
        options.add_argument("--headless")
        options.add_argument('--disable-logging')
        options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        options.add_argument('disable-gpu');
        options.add_argument('window-size=1200,1100');
        self.browser = Chrome(executable_path='/Users/mac/Documents/scrapping/chromedriver', options=options)
        self.browser.implicitly_wait(40)
        self.browser.get(ACE_URL)
        self.browser.maximize_window()
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
        expr = "./tr/td[@data-day="+str(date.day)+"]/button"
        # print (expr)
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
        # self.browser.find_element_by_class_name("l-hero__booking-action__submit--btn").click()
        self.browser.find_element_by_xpath("//span[@class='l-hero__booking-action__submit--btn-text']").click()


    def parseCars(self, ace):
        try:
            parsedCars = []
            cars = WebDriverWait(self.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-cars__cards"))
            cars = cars.find_elements_by_class_name("c-vehicle-card")
            totalCars = len(cars)+1
            # print ("Car Length:"+str(len(cars)))
            # print ("Total Cars Length:" +str(totalCars))

            for i in range(1,totalCars):
                parsedCar = {
                    "code":"",
                    "name": "",
                    "type": "",
                    "detail" : "",
                    "gear": "",
                    "seater":"",
                    "minSeats":"",
                    "maxSeats": "",
                    # "maxLuggage": "",
                    "photo": "",
                    "checkLuggage":"",
                    "carryLuggage":"",
                    # "carCost": "",
                    # "totalCost": "",
                    # "currencyCode": "",
                    "insuranceDetails": [],
                    "gps": ""
                }
                # Hide the itineray summary
                itemSummary = self.browser.find_element_by_class_name("l-booking-summary-bar")
                self.browser.execute_script("arguments[0].style.visibility='hidden'", itemSummary)
                action = ActionChains(self.browser)

                # print ("c-vehicle-card"+str([i]))
                # detailsButton = self.browser.find_elements_by_class_name("c-vehicle-card")[i].find_element_by_class_name("c-vehicle-card__action")

                detailsButtonExist = len(self.browser.find_elements_by_xpath("(//*[contains(@class,'c-vehicle-card__action')])"+str([i])))
                # print (self.browser.find_elements_by_xpath("(//*[contains(@class,'c-vehicle-card__action')])"+str([i])))

                if detailsButtonExist > 0:

                    detailsButton= self.browser.find_element_by_xpath("(//*[contains(@class,'c-vehicle-card__action')])"+str([i]))
                    action.move_to_element(detailsButton)
                    action.click(detailsButton).perform()
                    WebDriverWait(self.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-booking__step"))
                    parsedCar = self.parseCarDetail(self.browser, parsedCar)
                    parsedCars.append(parsedCar)
                    self.browser.back()
                    WebDriverWait(self.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-cars__cards"))
                else:
                    break

            return parsedCars
        except TimeoutException:
            print("Am i here in time out exception??")
            return parsedCars

    def parseCarDetail(self, carDetail, parsedCar):
        la=0
        extras = []
        elements = self.browser.find_elements_by_class_name("l-booking__step")
        inner = carDetail.find_element_by_class_name("l-vehicle-panel__inner")
        # insuranceDetails = elements[0].find_elements_by_class_name("c-option-card__main")
        insuranceDetails = elements[0].find_elements_by_xpath("//div[contains(@class,'c-option-card__main')]")
        liabilityDetails = elements[0].find_elements_by_xpath("//ul[@class='c-option-card__features']")
        # print (type(liabilityDetails))
        # time.sleep(3)
        # otherOptions = elements[1].find_elements_by_class_name("x-option-card__main")
        otherOptions = elements[1].find_elements_by_xpath("//*[contains(@class,'x-option-card__main')]")


        parsedCar["code"] = " "
        parsedCar["name"] = inner.find_element_by_class_name("l-vehicle-panel__subtitle").get_attribute("textContent")
        parsedCar["type"] = inner.find_element_by_class_name("l-vehicle-panel__title").get_attribute("textContent")
        parsedCar["photo"] = inner.find_element_by_class_name("l-vehicle-panel__image").find_element_by_xpath('./img').get_attribute("src")


        specifications = inner.find_element_by_class_name("l-vehicle-panel__specifications")
        parsedCar["detail"] = specifications.find_element_by_xpath('//img[contains(@src, "passengers")]').get_attribute("alt")+" , "+specifications.find_element_by_xpath('//img[contains(@src, "transmission")]').get_attribute("alt")
        parsedCar["gear"] = specifications.find_element_by_xpath('//img[contains(@src, "transmission")]').get_attribute("alt")
        parsedCar["seater"] = specifications.find_element_by_xpath('//img[contains(@src, "passengers")]').get_attribute("alt")
        parsedCar["minSeats"] = specifications.find_element_by_xpath('//img[contains(@src, "passengers")]').get_attribute("alt")
        parsedCar["maxSeats"] = specifications.find_element_by_xpath('//img[contains(@src, "passengers")]').get_attribute("alt")
        # parsedCar["maxLuggage"] = specifications.find_element_by_xpath('//img[contains(@src, "luggage")]').get_attribute("alt")
        parsedCar["checkLuggage"] = specifications.find_element_by_xpath('//img[contains(@src, "luggage")]').get_attribute("alt")
        parsedCar["carryLuggage"] = specifications.find_element_by_xpath('//img[contains(@src, "luggage")]').get_attribute("alt")



        cost = WebDriverWait(self.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-vehicle-panel__total"))
        # parsedCar["carCost"] = cost.find_element_by_class_name("l-vehicle-panel__total-item-total").get_attribute("textContent")
        # totalcost = cost.find_element_by_class_name("l-vehicle-panel__total-price")
        # parsedCar["currencyCode"] = totalcost.find_element_by_xpath('./span').get_attribute("textContent")
        # parsedCar["totalCost"] = totalcost.get_attribute("textContent")

        totalExtras=len(otherOptions)+1
        # print ("Total Extras"+str(totalExtras))

        for otherOption in otherOptions:

            for i in range(1,totalExtras):

                # print ("(//div[@class='x-option-card__title'])"+str([i]))

                extrasTitle=otherOption.find_element_by_xpath("(//div[@class='x-option-card__title'])"+str([i])).get_attribute("textContent")
                # print (extrasTitle)
                if "GPS" in extrasTitle:
                    parsedCar["gps"]= otherOption.find_element_by_xpath("(//div[@class='x-option-card__price'])"+str([i])).get_attribute("textContent")


        for _ins in insuranceDetails:
            la+=1

            # print ("Lia:"+str(la))
            # print ("Liability:"+liabilityDetails[la-1].find_element_by_xpath("(//*[@class='c-option-card__feature-detail'])[1]").get_attribute("textContent"))
            # print(type(_ins.find_elements_by_class_name( "c-option-card__price")))
            elementPresence = len(_ins.find_elements_by_class_name("c-option-card__price"))
            liabilityLen= len(liabilityDetails)
            # print ("Liability Length: "+str(liabilityLen))
            # print("length: "+str(elementPresence))

            if elementPresence > 0:
                insur = {
                            "name": _ins.find_element_by_class_name("c-option-card__title").get_attribute("textContent"),
                            "price": _ins.find_element_by_class_name("c-option-card__price").get_attribute("textContent"),
                            # "liability": liabilityDetails[la].find_element_by_xpath("//*[@class='c-option-card__feature-detail']").get_attribute("textContent")
                            "liability": liabilityDetails[la-1].find_element_by_xpath("(//*[@class='c-option-card__feature'][1]//*[@class='c-option-card__feature-detail'])"+str([la])).get_attribute("textContent")
                        }
            else:
                insur = {
                            "name": _ins.find_element_by_class_name("c-option-card__title").get_attribute("textContent"),
                            "price": "$0 NZD",
                            # "liability": liabilityDetails[la].find_element_by_xpath("//*[@class='c-option-card__feature-detail']").get_attribute("textContent")
                            "liability": liabilityDetails[la-1].find_element_by_xpath("(//*[@class='c-option-card__feature'][1]//*[@class='c-option-card__feature-detail'])"+str([la])).get_attribute("textContent")
                        }

            parsedCar["insuranceDetails"].append(insur)


        return parsedCar


    def tearDown(self):
        self.browser.quit()


@app.route("/")
def home():
    return "Scraper Service API"

@app.route("/getPickupLocations")
def getPickupLocations():
    ace = ACE()
    return jsonify({"locations": ace.dropDownOptions})

@app.route("/acefullscrapping", methods={'POST'})
def search():
    parsed=[]
    finalResponse=[]
    req = request.get_json()
    # print ("Request:"+str(req))
    newJson= json.dumps(req)
    reqDict = json.loads(newJson)
    lenreqDict= len(reqDict)
    # print("length"+str(lenreqDict))

    for x in range(0,lenreqDict):

            # print (reqDict.get(x))
            inpt= reqDict[x]
            # print ("Input Request"+str(inpt))
            ace = ACE()
            # ace.search(req)
            ace.search(inpt)
            parsed = ace.parseCars(ace)
            # parsed= parsed.append(ace.parseCars(ace))
            finalResponse.append(parsed)
            ace.tearDown()

    return jsonify({"parsed": finalResponse})

if __name__ == "__main__":
    app.run(debug=True)
    # ace = ACE()
     # ace.enterPromocode("HELLO")
    # ace.search({"pickupPoint": "Perth", "dropPoint": "Sydney", "pickupDate": "18/Nov/2019", "dropDate": "21/Nov/2019", "pickupTime": "09:00:00", "dropTime": "15:00:00"})
    # try:
    #     carsDOM = WebDriverWait(ace.browser, MAX_TIMEOUT).until(lambda x: x.find_element_by_class_name("l-cars__cards"))
    #     parsed = ace.parseCars(carsDOM)
    #     print("Parsed is ", parsed)
    # except TimeoutException:
    #     print("Loading took too much time!-Try again")
