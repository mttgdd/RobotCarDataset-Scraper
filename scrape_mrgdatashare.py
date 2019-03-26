#!/usr/bin/env python

'''
Downloads files matching patterns from the Oxford Robotcar Dataset website.

Matt Gadd
Jan 2018
Oxford Robotics Institute, Oxford University.

'''

# imports
import argparse
import datetime
from lxml import html
import os
import requests
import tarfile
import time
from tqdm import tqdm
import math

# urls
login_url = "https://mrgdatashare.robots.ox.ac.uk/"
datasets_url = "https://robotcar-dataset.robots.ox.ac.uk/datasets/"
base_download_url = "http://mrgdatashare.robots.ox.ac.uk:80/download/?filename=datasets/"

# responses
good_status_code = 200
failed_login = "Please try again or email for support"

# filesystem
file_extension = ".tar"
downloads_dir_example = os.path.expanduser("~/Downloads")

# throttle params
default_period_duration = 10 * 60
default_chunks_per_period = 1000
default_chunk_length = 1 * 1024


class Datasets:
    """Reads and provides a list of datasets to scrape via CL, input file.

        Attributes:
            datasets_file (string): Location of file with list of datasets to scrape.
            datasets (list): List of datasets along with file patterns that can be scraped.
    """

    def __init__(self, parse_args):
        """Loads dataset queries and list from CL and input file.

        Args:
            parse_args (list): List of input CL arguments.

        """

        # check datasets file
        self.datasets_file = Datasets.get_dataset_file(parse_args)

        # read datasets file
        self.datasets = Datasets.get_datasets(self.datasets_file)

    @staticmethod
    def get_dataset_file(parse_args):
        """Gets input file from CL.

        Args:
            parse_args (list): List of input CL arguments.

        Returns:
            string: Input file.

        Raises:
            IOError: When no input file is provided on the CL.

        """

        # check datasets file
        if not parse_args.datasets_file:
            raise IOError("Please specify option datasets_file.")
        return os.path.abspath(
            parse_args.datasets_file)

    @staticmethod
    def get_datasets(datasets_file):
        """Reads known datasets list and file patterns from input file.

        Args:
            datasets_file (string): Location of file with list of datasets to scrape.

        Returns:
            list: Known datasets list.

        """

        print("reading datasets_file: " + datasets_file)
        datasets = []
        with open(datasets_file, "r") as file_handle:
            lines = file_handle.readlines()
            for line in lines:
                line = line.strip("\n").split(",")
                dataset = {"dataset": line[0], "file_patterns": line[1:]}
                datasets.append(dataset)
        print("got num_datasets: " + str(len(datasets)))
        return datasets


class Scraper:
    """Maintains login session and performs file requests.

            Attributes:
                username (string): RCD login username.
                password (string): RCD login password.
                session_requests (requests.Session): Persistent login session.
    """

    def __init__(self, parse_args):
        """Sets up credentials and starts login session.

        Args:
            parse_args (list): List of input CL arguments.

        """

        # credentials
        self.username = Scraper.get_username(parse_args)
        self.password = Scraper.get_password(parse_args)

        # persistent login session
        self.session_requests = requests.session()

    @staticmethod
    def get_username(parse_args):
        """Retrieves account details from CL.

        Args:
            parse_args (list): List of input CL arguments.

        Returns:
            string: Username.

        Raises:
            IOError: If username is not provided on the CL.

        """

        if not parse_args.username:
            raise IOError("Please specify option username.")
        return parse_args.username

    @staticmethod
    def get_password(parse_args):
        """Retrieves login password from CL.

        Args:
            parse_args (list): List of input CL arguments.

        Returns:
            string: Password.

        Raises:
            IOError: If password is not provided on the CL.

        """

        if not parse_args.password:
            raise IOError("Please specify option password.")
        return parse_args.password

    def login(self):
        """Initialises the login session using credentials.

        """

        # get middleware token
        csrf_middleware_token = self.get_csrf_middleware_token()

        # login dictionary payload
        payload = self.get_payload(csrf_middleware_token)

        # perform login
        self.post(payload)

    def get_csrf_middleware_token(self):
        """Retrieve authentication token from login session cookies.

        Returns:
            string: Authentication token from cookies.

        """

        # load cookies
        result = self.session_requests.get(login_url)
        tree = html.fromstring(result.text)

        # get authentication token
        csrf_middleware_token = list(
            set(tree.xpath("//input[@name='csrfmiddlewaretoken']/@value")))[0]
        print("got csrf_middleware_token: " + csrf_middleware_token)

        return csrf_middleware_token

    def get_payload(self, csrf_middleware_token):
        """Prepare login dictionary payload.

        Args:
            csrf_middleware_token (string): Authentication token from cookies.

        Returns:
            dict: Login credentials and cookies.

        """

        return {"username": self.username,
                "password": self.password,
                "csrfmiddlewaretoken": csrf_middleware_token}

    def post(self, payload):
        """Sends payload to login session (logs in).

        Args:
            payload (dict): Login credentials and cookies.

        Raises:
            ValueError: If login credentials did not work.

        """

        # post login data
        result = self.session_requests.post(
            login_url,
            data=payload,
            headers=dict(referer=login_url)
        )

        # get status code
        status_code = result.status_code

        # check for success
        text = result.text
        if status_code != good_status_code or failed_login in text:
            raise ValueError("Login failed, check username and password.")

        print("Logged in!")

    def scrape(self, url_handler):
        """Downloads a sensor log from a particular dataset.

        Args:
            url_handler (URLHandler): Local file path for the sensor log to be downloaded.

        """

        # make request
        print("requesting file_url: " + url_handler.file_url)
        result = self.session_requests.get(url_handler.file_url, stream=True)
        if result.status_code != good_status_code:
            raise ValueError(
                "bad file_url: " +
                url_handler.file_url)

        # open local file
        print(
                "downloading local_file_path: " +
                url_handler.local_file_path)
        file_handle = open(url_handler.local_file_path, 'wb')

        # iterate chunks
        total_size = int(result.headers.get('content-length', 0))
        for chunk in tqdm(result.iter_content(
                chunk_size=throttle.chunk_length),
                total=math.ceil(total_size // int(throttle.chunk_length)),
                unit='KB',
                unit_scale=True):
            # bad url/no match for sensor
            if b"File not found." in chunk:
                return False

            # count recent chunks
            throttle.count()

            # filter out keep-alive new chunks
            if chunk:
                file_handle.write(chunk)

        # close local file
        file_handle.close()

        return True


class Throttle:
    """Forces downloads to obey a conservative limit.

            Attributes:
                period_duration (int): Top limit for duration of download window.
                chunk_length (int): Top limit for size of chunks in bytes.
                chunks_per_period (int): Top limit for chunks downloaded in one period.
                num_chunks_in_period (int): Chunks downloaded in this period.
                period (datetime.datetime): Timestamp.
    """

    def __init__(self, parse_args):
        """Initialises download throttling window.

        Args:
            parse_args (list): List of input CL arguments.

        """

        # length of throttling period
        self.period_duration = Throttle.get_period_duration(parse_args)

        # data size
        self.chunk_length = Throttle.get_chunk_length(parse_args)

        # throttle limit
        self.chunks_per_period = Throttle.get_chunks_per_period(
            parse_args)

        # reset counters
        self.num_chunks_in_period = 0
        self.period = datetime.datetime.now()

    @staticmethod
    def get_period_duration(parse_args):
        """Gets period length from CL.

        Args:
            parse_args (list): List of input CL arguments.

        Returns:
            string: Period length.

        Raises:
            IOError: If period length was not provided on the CL.

        """

        if not parse_args.period_duration:
            raise IOError("Please specify option period_duration.")
        return parse_args.period_duration

    @staticmethod
    def get_chunk_length(parse_args):
        """Gets chunk size from CL.

        Args:
            parse_args (list): List of input CL arguments.

        Returns:
            string: Chunk size.

        Raises:
            IOError: If chunk size was not provided on the CL.

        """

        if not parse_args.chunk_length:
            raise IOError("Please specify option chunk_length.")
        return parse_args.chunk_length

    @staticmethod
    def get_chunks_per_period(parse_args):
        """Get throttle from CL.

        Args:
            parse_args (list): List of input CL arguments.

        Returns:
            string: Throttle.

        Raises:
            IOError: If throttle was not provided on the CL.

        """

        if not parse_args.chunks_per_period:
            raise IOError("Please specify option chunks_per_period.")
        return parse_args.chunks_per_period

    def reset(self):
        """Resets throttle counters.

        """

        print("resetting period throttle...")
        self.num_chunks_in_period = 0
        self.period = datetime.datetime.now()

    def wait(self):
        """Forces the downloader to obey throttle limit by idling.

        """

        # reset period count
        period_seconds = self.get_period_seconds()

        # needs reset
        if period_seconds < 0:
            self.reset()
        # needs to pause
        elif self.num_chunks_in_period > self.chunks_per_period:
            Throttle.pause(period_seconds)

    def get_period_seconds(self):
        """Computes the time remaining in this throttle window.

        Returns:
            int: Time remaining in this throttle window.

        """

        period_seconds = self.period_duration - \
                         (datetime.datetime.now() - self.period).seconds
        # console
        print("num_chunks_in_period: " + str(self.num_chunks_in_period) +
              ", period_seconds: " + str(period_seconds))
        return period_seconds

    @staticmethod
    def pause(period_seconds):
        """Idles.

        """

        print(
                "pausing for throttle for period_seconds: " +
                str(period_seconds) +
                "...")
        time.sleep(period_seconds)

    def count(self):
        """Increments the number of chunks retrieved in this throttle window.

        """

        self.num_chunks_in_period = self.num_chunks_in_period + 1


class DatasetHandler:
    """Manages local file paths for a dataset to be downloaded.

            Attributes:
                downloads_dir (string): Root download directory.
                dataset (string): Dataset to download.
                dataset_dir (string): Dataset's download directory.
                tar_dir (string): Extraction directory.
    """

    def __init__(self, parse_args, dataset):
        """Initialises local file paths for downloads concerning this dataset.

        Args:
            parse_args (list): List of input CL arguments.
            dataset (string): Dataset to download.

        """

        # root download dir
        self.downloads_dir = DatasetHandler.get_downloads_dir(parse_args)

        # dataset to download
        self.dataset = dataset

    @staticmethod
    def get_downloads_dir(parse_args):
        """Gets the root download directory from the CL.

        Args:
            parse_args (list): List of input CL arguments.

        Returns:
            string: Absolute path to root downloads directory.

        Raises:
            IOError: If root download directory was not provided on the CL.

        """

        if not parse_args.downloads_dir:
            raise IOError("Please specify option downloads_dir.")
        return os.path.abspath(parse_args.downloads_dir)


class Zipper:
    """Performs archiving operations on local file system.

            Attributes:
                dataset_handler (DatasetHandler): Local file paths for this dataset to be downloaded.
                num_successful_unzipped (int): Number of successful archiving operations.
    """

    def __init__(self, dataset_handler):
        """Initialises an archiver for this downloaded dataset.

        Args:
            dataset_handler (DatasetHandler): Local file paths for this dataset to be downloaded.

        """

        self.dataset_handler = dataset_handler
        self.num_successful_unzipped = 0

    # unzip
    def unzip(self, url_handler):
        """Extracts archive contents.

        Args:
            url_handler (URLHandler): Local file path for the sensor log to be downloaded.

        """

        print("unzipping local_file_path: " + url_handler.local_file_path)
        try:
            # open tar
            tar = tarfile.open(url_handler.local_file_path, "r:")

            # do extraction
            tar.extractall(path=self.dataset_handler.downloads_dir)

            # close tar file
            tar.close()

            # keep track of successful archives
            self.num_successful_unzipped = self.num_successful_unzipped + 1
        except tarfile.ReadError:
            print(
                    "failed when unzipping local_file_path: " +
                    url_handler.local_file_path)

        # clear tar
        os.remove(url_handler.local_file_path)

    def tidy_up(self):
        """Tidies up dataset's download directory.

        """

        # tidy up
        print("tidying up dataset: " + self.dataset_handler.dataset)


class URLHandler:
    """Manages local file paths for a file pattern and dataset combination.

            Attributes:
                file_pattern (string): Sensor type / file stub.
                file_url (string): URL target path.
                local_file_path (string): Local file system destination path.
    """

    def __init__(self, dataset_handler, file_pattern):
        """Initialises the download of one file type for this dataset.

        Args:
            dataset_handler (DatasetHandler): Local file paths for this dataset to be downloaded.
            file_pattern (string): Sensor type to download.

        """

        # file pattern
        self.file_pattern = file_pattern

        # URL
        self.file_url = URLHandler.get_file_url(
            self.file_pattern, dataset_handler)

        # path to save to disk
        self.local_file_path = URLHandler.get_local_file_path(
            self.file_url, dataset_handler)

    @staticmethod
    def get_file_url(file_pattern, dataset_handler):
        """Constructs URL for sensor log.

        Args:
            file_pattern (string): Sensor type to download.
            dataset_handler (DatasetHandler): Local file paths for this dataset to be downloaded.

        Returns:
            string: Internet address for the sensor log in this dataset.

        """

        return base_download_url + dataset_handler.dataset + "/" + \
               dataset_handler.dataset + "_" + file_pattern + file_extension

    @staticmethod
    def get_local_file_path(file_url, dataset_handler):
        """Constructs filesystem location for sensor log.

        Args:
            file_url (string): Internet address for the sensor log in this dataset.
            dataset_handler (DatasetHandler): Local file paths for this dataset to be downloaded.

        Returns:
            string: Destination filesystem location for sensor log.

        """

        # get stem from ULR
        local_file_name = file_url.split('/')[-1]

        # extend dataset dir
        local_file_path = os.path.join(
            dataset_handler.downloads_dir, local_file_name)

        return local_file_path


# main routine
if __name__ == "__main__":
    # console
    print("ScrapeMRGDatashare is starting...")

    # option parsing suite
    argument_parser = argparse.ArgumentParser(
        description="ScrapeMRGDatashare input parameters")

    # specify CL args
    argument_parser.add_argument(
        "--username",
        dest="username",
        help="Registered username for " + login_url)
    argument_parser.add_argument(
        "--password",
        dest="password",
        help="Registered password for " + login_url)
    argument_parser.add_argument(
        "--datasets_file",
        dest="datasets_file",
        help="List of dataset names from " +
             datasets_url + " - separated by new lines.")
    argument_parser.add_argument(
        "--downloads_dir",
        dest="downloads_dir",
        default=downloads_dir_example,
        help="Root download directory e.g. " + downloads_dir_example)
    argument_parser.add_argument(
        "--period_duration",
        dest="period_duration",
        type=int,
        default=default_period_duration,
        help="Length of throttled download period in seconds e.g. " +
             str(default_period_duration))
    argument_parser.add_argument(
        "--chunk_length",
        dest="chunk_length",
        type=int,
        default=default_chunk_length,
        help="Length of download chunks in bytes e.g. " +
             str(default_chunk_length))
    argument_parser.add_argument(
        "--chunks_per_period",
        dest="chunks_per_period",
        type=int,
        default=default_chunks_per_period,
        help="Maximum number of chunks to download in a throttled download period e.g. " +
             str(default_chunks_per_period))

    # parse CL
    parse_args = argument_parser.parse_args()

    # set up datasets file
    datasets = Datasets(parse_args).datasets

    # persistent login
    scraper = Scraper(parse_args)

    # load cookies
    scraper.login()

    # start throttle
    throttle = Throttle(parse_args)

    # iterate datasets
    for dataset in datasets:
        # apply throttle
        throttle.wait()

        # dataset handler
        dataset_handler = DatasetHandler(parse_args, dataset["dataset"])

        # set up zipper
        zipper = Zipper(dataset_handler)

        # iterate file patterns
        for file_pattern in dataset["file_patterns"]:
            # set up URL handler
            url_handler = URLHandler(dataset_handler, file_pattern)

            # perform download
            file_was_found = scraper.scrape(url_handler)

            # unzip
            if file_was_found:
                zipper.unzip(url_handler)

        # tidy up
        zipper.tidy_up()

    # console
    print("ScrapeMRGDatashare is finished!")
