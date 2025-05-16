import time
import re
import os
import threading
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scraping_model.models import Car
from concurrent.futures import ThreadPoolExecutor

load_dotenv()
NUM_PAGES = int(os.getenv('SCRAPER_NUM_PAGES', 1))
NUM_WORKERS = int(os.getenv('SCRAPER_NUM_WORKERS', 6))

thread_local = threading.local()

def parse_odometer(odometer_str):
    odometer_str = odometer_str.lower()
    odometer_str = odometer_str.replace('\xa0', '').replace(' ', '').replace('.', '').replace(',', '')
    digits = ''.join(re.findall(r'\d+', odometer_str))
    if not digits:
        return 0
    num = int(digits)
    return num * 1000


def get_odometer_from_soup(soup):

    selectors = [
        "span.size18",
        ".base-information span",
        ".js-race",
    ]
    for selector in selectors:
        tags = soup.select(selector)
        for tag in tags:
            txt = tag.get_text(strip=True)
            if "км" in txt or "тис" in txt or txt.isdigit():
                return parse_odometer(txt)

    m = re.search(r'([\d\.\,\s\xa0]+)\s*(тис\.?)?\s*км', soup.get_text())
    if m:
        return parse_odometer(m.group(0))
    return 0

def extract_digits(text):
    digits = re.findall(r'\d+', text.replace('\xa0', ' '))
    return int(''.join(digits)) if digits else 0

def get_title(soup):
    for selector in ['h1.head', 'div.size20.bold.mb-8', '.auto-content_title', '.heading']:
        tag = soup.select_one(selector)
        if tag and tag.text.strip():
            return tag.text.strip()
    return ''

def get_price_usd(soup):
    selectors = [
        'span.size32', 'span.size30',
        'strong.common-text.ws-pre-wrap.title',
        '.price-ticket', '.price_value', '.size22'
    ]
    for sel in selectors:
        for tag in soup.select(sel):
            text = tag.get_text(strip=True)
            if '$' in text:
                val = extract_digits(text)
                if 100 < val < 300000:
                    return val
    m = re.search(r'([\d \xa0]{3,})\$', soup.get_text())
    if m:
        val = extract_digits(m.group(1))
        if 100 < val < 300000:
            return val
    return 0

def get_vin(soup):
    vin = ''
    tags = [
        soup.select_one(".vin-code"),
        soup.select_one("span.common-text.ws-pre-wrap.badge"),
    ]
    for tag in tags:
        if tag and tag.text.strip() and len(tag.text.strip()) >= 17:
            vin = tag.text.strip()
            break
    if not vin:
        label = soup.find("div", class_="label", string=lambda t: t and "VIN" in t)
        if label:
            value_div = label.find_next_sibling("div", class_="value")
            if value_div:
                if value_div.has_attr("title") and len(value_div["title"].strip()) >= 17:
                    vin = value_div["title"].strip()
                elif value_div.text and len(value_div.text.strip()) >= 17:
                    vin = value_div.text.strip()
    if not vin:
        vin_text = soup.find(string=re.compile(r'VIN[-\s]?код', re.IGNORECASE))
        if vin_text:
            vin_regex = re.compile(r'\b[A-HJ-NPR-Z0-9]{17}\b')
            m = vin_regex.search(vin_text)
            if m:
                vin = m.group(0)
            else:
                parent = vin_text.parent
                for sibling in parent.next_siblings:
                    text = getattr(sibling, 'text', None)
                    if text:
                        m2 = vin_regex.search(text)
                        if m2:
                            vin = m2.group(0)
                            break
    if not vin:
        vin_matches = re.findall(r'\b[A-HJ-NPR-Z0-9]{17}\b', soup.get_text())
        if vin_matches:
            vin = vin_matches[0]
    if not vin:
        vin = "Проблема з VIN кодом"
    return vin

def get_car_number(soup):
    tag = soup.select_one(".state-num")
    if tag:
        text = tag.text.strip()
        m = re.match(r"^([A-ZА-ЯІЇЄ]{2,3}\s?\d{3,4}\s?[A-ZА-ЯІЇЄ]{2,3})", text)
        if m:
            return m.group(1).replace('  ', ' ').strip()
    return "Номер автомобіля відсутній"

def get_username(soup):
    user_tag = (
        soup.select_one('.seller_info_name') or
        soup.select_one('.seller_info__name') or
        soup.select_one('.seller_info_name_top') or
        soup.select_one('.person-link')
    )
    username = user_tag.text.strip() if user_tag else ""
    if not username or "продан" in username.lower():
        return "Машина продана"
    return username

def extract_phones_from_soup(soup):
    phones = set()
    tel_links = soup.find_all('a', href=re.compile(r'^tel:'))
    for link in tel_links:
        num = re.sub(r'\D', '', link.get('href', ''))
        if 9 <= len(num) <= 12:
            phones.add(num)
    pattern = re.compile(r'(?:\+?38)?0\d{9}')
    for t in soup.stripped_strings:
        found = pattern.findall(t)
        for num in found:
            clean_num = re.sub(r'\D', '', num)
            if 9 <= len(clean_num) <= 12:
                phones.add(clean_num)
    return ", ".join(phones) if phones else "-"

def close_all_cookie_popups(driver):
    xpaths = [
        "//button[contains(., 'Согласиться')]", "//button[contains(., 'Понимаю и разрешаю')]",
        "//button[contains(., 'Принять')]", "//button[contains(., 'Продовжити')]", "//button[contains(., 'Далі')]",
        "//button[contains(., 'OK')]", "//button[contains(., 'Agree')]", "//button[contains(., 'Accept')]",
        "//button[contains(., 'Настроить')]", "//button[contains(., 'Отказаться')]", "//button[contains(., 'Відмовитись')]",
        "//button[contains(., 'Decline')]", "//button[contains(., 'Зрозуміло')]", "//button[contains(., 'Закрити')]",
    ]
    for _ in range(2):
        for xpath in xpaths:
            try:
                btn = WebDriverWait(driver, 1).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                btn.click()
            except Exception:
                continue
        time.sleep(0.1)

def find_phone_buttons(driver):
    xpaths = [
        "//button[contains(.,'Показати номер') or contains(.,'Показать номер') or contains(.,'XXX')]",
        "//span[contains(.,'Показати номер') or contains(.,'Показать номер') or contains(.,'XXX')]",
        "//div[contains(.,'Показати номер') or contains(.,'Показать номер') or contains(.,'XXX')]",
        "//*[@data-testid='show-phone']",
        "//button[contains(@aria-label, 'Показати номер') or contains(@aria-label, 'Показать номер')]",
        "//a[contains(@href, 'tel:')]"
    ]
    all_btns = []
    for xp in xpaths:
        try:
            btns = driver.find_elements(By.XPATH, xp)
            if btns:
                all_btns += btns
        except Exception:
            continue
    return all_btns

def get_driver():
    if not hasattr(thread_local, "driver"):
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument("--remote-debugging-port=0")
        chrome_options.add_experimental_option("prefs", {
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.notifications": 2
        })
        driver = webdriver.Chrome(options=chrome_options)
        thread_local.driver = driver
    return thread_local.driver

def get_phone_number_selenium(driver, url, debug_id=""):
    driver.get(url)
    driver.set_window_size(1920, 1080)
    close_all_cookie_popups(driver)
    found_phone = set()
    btns = find_phone_buttons(driver)
    for btn in btns:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
            try:
                btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", btn)
            time.sleep(0.08)
        except Exception:
            continue
    page = driver.page_source
    soup = BeautifulSoup(page, "lxml")
    tel_links = soup.find_all('a', href=re.compile(r'^tel:'))
    for link in tel_links:
        num = re.sub(r'\D', '', link.get('href', ''))
        if 9 <= len(num) <= 12:
            found_phone.add(num)
    if not found_phone:
        pattern = re.compile(r'(?:\+?38)?0\d{9}')
        for t in soup.stripped_strings:
            found = pattern.findall(t)
            for num in found:
                clean_num = re.sub(r'\D', '', num)
                if 9 <= len(clean_num) <= 12:
                    found_phone.add(clean_num)
    if not found_phone:
        print(f"[Phone Selenium] На {url} номер НЕ знайдено (debug_id={debug_id})")
        return "-"
    print(f"[Phone Selenium] На {url} знайдено: {', '.join(found_phone)}")
    return ", ".join(found_phone)

def get_car_details(url, driver):
    session = requests.Session()
    resp = session.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "lxml")
    title = get_title(soup)
    price_usd = get_price_usd(soup)
    car_vin = get_vin(soup)
    car_number = get_car_number(soup)
    username = get_username(soup)
    img_tag = (
        soup.select_one(".photo-620x465 img") or
        soup.select_one("img.outline.mhide") or
        soup.select_one("img.carousel-img")
    )
    image_url = img_tag["src"] if img_tag and img_tag.has_attr("src") else ""
    images = soup.select(".thumbnails img, .photo-620x465 img, .carousel-img")
    images_count = len(images)
    phone_number = extract_phones_from_soup(soup)
    odometer = get_odometer_from_soup(soup)
    if phone_number == "-" or not phone_number.strip():
        debug_id = url.split("/")[-1].replace(".html", "")
        phone_number = get_phone_number_selenium(driver, url, debug_id)
    return {
        "url": url,
        "title": title,
        "price_usd": price_usd,
        "car_vin": car_vin,
        "car_number": car_number,
        "username": username,
        "phone_number": phone_number,
        "image_url": image_url,
        "images_count": images_count,
        "odometer": odometer
    }

def process_car_url(url):
    driver = get_driver()
    try:
        if not Car.objects.filter(url=url).exists():
            details = get_car_details(url, driver)
            Car.objects.create(
                url=details["url"],
                title=details["title"],
                price_usd=details["price_usd"],
                odometer=details["odometer"],
                username=details["username"],
                phone_number=details["phone_number"],
                image_url=details["image_url"],
                images_count=details["images_count"],
                car_number=details["car_number"],
                car_vin=details["car_vin"]
            )
            print(f"[SAVED] {details['title']} - {details['phone_number']} [{details['odometer']}]")
    except Exception as e:
        print(f"[ERROR] {url}: {e}")


def get_all_listing_pages(base_url, num_pages=NUM_PAGES):
    print(f"Парсимо {num_pages} сторінок!")
    return [f"{base_url}?page={i}" for i in range(1, num_pages + 1)]


def get_all_car_urls(base_url, num_pages=NUM_PAGES):
    listing_pages = get_all_listing_pages(base_url, num_pages=num_pages)
    cars = []
    for page_url in listing_pages:
        print(f"Парсинг сторінки: {page_url}")
        response = requests.get(page_url)
        soup = BeautifulSoup(response.text, "lxml")
        car_blocks = soup.select('.content-bar')
        for car in car_blocks:
            url_tag = car.select_one('a.address')
            url = url_tag['href'] if url_tag else ''
            if url:
                cars.append(url)
        time.sleep(0.1)
    return cars


def scrape_autoria(num_workers=NUM_WORKERS):
    base_url = "https://auto.ria.com/car/used/"
    cars = get_all_car_urls(base_url, num_pages=NUM_PAGES)
    print(f"Found {len(cars)} cars to process")
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        executor.map(process_car_url, cars)
    try:
        if hasattr(thread_local, "driver"):
            thread_local.driver.quit()
    except Exception:
        pass


if __name__ == '__main__':
    scrape_autoria(num_workers=NUM_WORKERS)
    print("Scraping done!")
