import csv
import re
import threading
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

gecko_driver_path = "geckodriver"
product_scrapping_thread_pool = 1
review_scrapping_thread_pool = 1

# function to check wheter an element is
# found or not
def check_element(driver, by, locator):
    try:
        driver.find_element(by, locator)

        return True
    except NoSuchElementException:
        return False


# function to scrap reviews from a
# certain product
def scrap_reviews(url, last_page=1):
    print("Scrapping product: %s" % url)

    # define the path of our chromedriver
    global gecko_driver_path

    # define options to launch
    # the driver
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920x1080")

    # init chrome
    driver = webdriver.Firefox(executable_path=gecko_driver_path, options=options)

    # go to 'url'
    driver.get(url)

    # wait for 0.3s to make sure
    # the page is fully loaded
    time.sleep(1)
    # scroll to bottom to load
    # reviews
    driver.execute_script("window.scrollTo(0,500)")

    current_page = last_page
    # loop through all reviews
    while True:
        # define a desired class
        class_regex_string = "shopee-button-solid--primary"

        try:
            WebDriverWait(driver, 60).until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, ".product-ratings__list")
                )
            )
        except TimeoutError as err:
            print(err)
            driver.close()
            return

        # find element that wrapped
        # all reviews
        product_review_wrapper = driver.find_element(
            By.CSS_SELECTOR, ".product-ratings__list"
        )

        try:
            # wait until pagination button is presence
            # in review page
            WebDriverWait(driver, 60).until(
                expected_conditions.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        "button.shopee-icon-button.shopee-icon-button--left",
                    )
                )
            )

            current_selected_page_raw = product_review_wrapper.find_element(
                By.CSS_SELECTOR, ".shopee-button-solid.shopee-button-solid--primary"
            ).get_attribute("innerText")
            current_selected_page = int(current_selected_page_raw)

            # get prev page button
            product_review_prev_button = product_review_wrapper.find_element(
                By.CSS_SELECTOR, "button.shopee-icon-button.shopee-icon-button--left"
            )
            # get next page button
            product_review_next_button = product_review_wrapper.find_element(
                By.CSS_SELECTOR, "button.shopee-icon-button.shopee-icon-button--right"
            )
            while current_selected_page < current_page:
                product_review_next_button.click()
                current_selected_page_raw = product_review_wrapper.find_element(
                    By.CSS_SELECTOR, ".shopee-button-solid.shopee-button-solid--primary"
                ).get_attribute("innerText")
                current_selected_page = int(current_selected_page_raw)
            while current_selected_page > current_page:
                product_review_prev_button.click()
                current_selected_page_raw = product_review_wrapper.find_element(
                    By.CSS_SELECTOR, ".shopee-button-solid.shopee-button-solid--primary"
                ).get_attribute("innerText")
                current_selected_page = int(current_selected_page_raw)
        except:
            print("error")
            driver.close()
            return scrap_reviews(url, current_page)

        # get next page button
        product_review_next_button = product_review_wrapper.find_element(
            By.CSS_SELECTOR, "button.shopee-icon-button.shopee-icon-button--right"
        )
        # get last page button
        product_review_last_page = product_review_wrapper.find_element(
            By.CSS_SELECTOR,
            ".shopee-page-controller.product-ratings__page-controller button:nth-last-child(2)",
        )
        # get last page class
        product_review_last_page_class = product_review_last_page.get_attribute("class")
        try:
            # wait until the top comment is loaded
            WebDriverWait(driver, 60).until(
                expected_conditions.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.shopee-product-rating:nth-child(1)")
                )
            )

            # get element that wrapped all reviews
            reviews_wrapper = product_review_wrapper.find_element(By.XPATH, "./div[1]")
            # get all childs of the wrapper
            reviews = reviews_wrapper.find_elements(By.XPATH, "./div")
            # loop through review's element
            for i in range(0, len(reviews)):
                review = reviews[i]

                review_user = (
                    review.find_element(
                        By.CSS_SELECTOR, "div.shopee-product-rating__author-name"
                    ).get_attribute("innerText")
                    if (
                        check_element(
                            review,
                            By.CSS_SELECTOR,
                            "div.shopee-product-rating__author-name",
                        )
                    )
                    else ""
                )
                review_rating = len(
                    review.find_elements(
                        By.CSS_SELECTOR,
                        "div.shopee-product-rating__rating svg.shopee-svg-icon.icon-rating-solid--active.icon-rating-solid",
                    )
                )
                review_comment = (
                    review.find_element(By.CSS_SELECTOR, "div._3NrdYc").get_attribute(
                        "innerText"
                    )
                    if (check_element(review, By.CSS_SELECTOR, "div._3NrdYc"))
                    else ""
                )

                # define a dictionary to save the review
                data = dict(comment=review_comment)
                data_with_rating = dict(
                    user=review_user, rating=review_rating, comment=review_comment
                )
                # write the review to 'csv' file
                with open("reviews.csv", "a") as f:
                    w = csv.writer(f)
                    w.writerow(data.values())
                    f.close()
                with open("reviews-with-rating.csv", "a") as f:
                    w = csv.writer(f)
                    w.writerow(data_with_rating.values())
                    f.close()

            # check, if the last page button contain
            # a desired class, then break the loop
            if re.search(class_regex_string, product_review_last_page_class):
                break
        except:
            print("Loading timeout")

        # go to the next page
        product_review_next_button.click()
        current_page += 1

    driver.close()


# run scrapping in GPU
def scrap_products(page):
    print("Scrapping page: %s" % page)

    global gecko_driver_path, review_scrapping_thread_pool
    urls = []

    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920x1080")

    driver = webdriver.Firefox(executable_path=gecko_driver_path, options=options)

    driver.get("https://shopee.co.id/shop/25303916/search?page=%d" % page)

    # wait until products is loaded
    WebDriverWait(driver, 60).until(
        expected_conditions.presence_of_element_located(
            (
                By.XPATH,
                "/html/body/div[1]/div/div[3]/div/div/div[2]/div/div[2]/div/div[1]",
            )
        )
    )

    # get element that wrapped all products
    product_wrapper = driver.find_element(
        By.XPATH, "/html/body/div[1]/div/div[3]/div/div/div[2]/div/div[2]/div"
    )
    # get all products
    products = product_wrapper.find_elements(By.XPATH, "./div")
    # loop through products
    for i in range(0, len(products)):
        # check if the product has 'a' element
        if check_element(
            driver,
            By.XPATH,
            "/html/body/div[1]/div/div[3]/div/div/div[2]/div/div[2]/div/div[%d]/a" % i,
        ):
            # check if the product has rating
            if check_element(
                driver,
                By.XPATH,
                "/html/body/div[1]/div/div[3]/div/div/div[2]/div/div[2]/div/div[%d]/a/div/div/div[2]/div[3]/div[2]/div"
                % i,
            ):
                # get product 'a' element
                product = driver.find_element(
                    By.XPATH,
                    "/html/body/div[1]/div/div[3]/div/div/div[2]/div/div[2]/div/div[%d]/a"
                    % i,
                )
                # append product url to urls
                urls.append(product.get_attribute("href"))

    driver.close()

    # loop through all urls to get
    # their reviews
    for i in range(0, len(urls), review_scrapping_thread_pool):
        threads = list()
        for j in range(review_scrapping_thread_pool):
            if i + j < len(urls):
                x = threading.Thread(target=scrap_reviews, args=(urls[i + j],))
                threads.append(x)
                x.start()

        for thread in threads:
            thread.join()


def main():
    global gecko_driver_path, product_scrapping_thread_pool

    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920x1080")

    driver = webdriver.Firefox(executable_path=gecko_driver_path, options=options)

    driver.get("https://shopee.co.id/shop/25303916/search?page=0")

    WebDriverWait(driver, 60).until(
        expected_conditions.presence_of_element_located(
            (
                By.XPATH,
                "/html/body/div[1]/div/div[3]/div/div/div[2]/div/div[1]/div[2]/div/span[2]",
            )
        )
    )

    time.sleep(1)
    # get last page of merchant products
    last_page = int(
        driver.find_element(
            By.XPATH,
            "/html/body/div[1]/div/div[3]/div/div/div[2]/div/div[1]/div[2]/div/span[2]",
        ).get_attribute("innerText")
    )

    # range(start, end, step)
    # 0, 2, 4
    # 0, 3, 6
    for i in range(0, last_page, product_scrapping_thread_pool):
        threads = list()
        for j in range(product_scrapping_thread_pool):
            if i + j < last_page:
                x = threading.Thread(target=scrap_products, args=(i + j,))
                threads.append(x)
                x.start()

        for thread in threads:
            thread.join()


if __name__ == "__main__":
    # Create file csv with header
    with open("reviews.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(dict(comment="").keys())
    with open("reviews-with-rating.csv", "w") as f:
        w = csv.writer(f)
        w.writerow(dict(user="", rating="", comment="").keys())

    main()
