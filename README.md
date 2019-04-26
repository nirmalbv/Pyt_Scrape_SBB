# Pyt_Scrape_SBB

The sbb folder consists of a scraping file.

### Dependencies that need to be satisfied before.
* Download the geckdodriver - mozilla driver
* Extract the file and make it accessible. (PATH variable)
* Install selenium

### Geckodriver - Installation
* wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz
* tar xvfz geckodriver-v0.24.0-linux64.tar.gz
* mv geckodriver ~/.local/bin .

my path variable contains this path. Change this statement to move to a folder which is already present in the path variable. 

### Install Selenium
* pip install selenium

Hopefully, the python environment that is set already isn't deleted or modified.


### Run the file.
python scrape.py
