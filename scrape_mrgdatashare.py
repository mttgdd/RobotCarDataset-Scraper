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
import shutil
import tarfile
import time

# urls
login_url = "https://mrgdatashare.robots.ox.ac.uk/"
datasets_url = "http://robotcar-dataset.robots.ox.ac.uk/datasets/"
base_download_url = "http://mrgdatashare.robots.ox.ac.uk:80/download/?filename=datasets/"

# responses
good_status_code = 200
failed_login = "Please try again or email for support"

# filesystem
dataset_example = "2014-05-06-12-54-54"
tmp_dir = "/tmp"
file_pattern_example = "vo"
file_extension = ".tar"
downloads_dir_example = os.path.expanduser("~/Downloads")
wildcard = "*"

# throttle
default_period_duration = 10 * 60
default_chunks_per_period = 1000
default_chunk_length = 1 * 1024


class Datasets:
    """Reads and provides a list of datasets to scrape via CL, input file.

        Attributes:
            dataset (string): Dataset to scrape.
            datasets_file (string): Location of file with list of datasets to scrape.
            datasets (list): List of datasets that can be scraped.
    """

    def __init__(self, parse_args):
        """Loads dataset queries and list from CL and input file.

        Args:
            parse_args (list): List of input CL arguments.

        """

        # sanitise target dataset on CL
        self.dataset = Datasets.get_dataset(parse_args)

        # check datasets file
        self.datasets_file = Datasets.get_dataset_file(parse_args)

        # read datasets file
        self.datasets = Datasets.get_datasets(self.datasets_file)

        # validate dataset
        self.validate()

    @staticmethod
    def get_dataset(parse_args):
        """Gets query dataset from CL.

        Args:
            parse_args (list): List of input CL arguments.

        Returns:
            string: Dataset to scrape.

        Raises:
            IOError: When no dataset is provided on the CL.

        """

        if not parse_args.dataset:
            raise IOError("Please specify option dataset.")
        return parse_args.dataset

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
        """Reads known datasets list from input file.

        Args:
            datasets_file (string): Location of file with list of datasets to scrape.

        Returns:
            list: Known datasets list.

        """

        datasets = [line.rstrip('\n')[:19] for line in open(
            datasets_file)]
        print("got num_datasets: " + str(len(datasets)))
        return datasets

    def validate(self):
        """Sanity checks query dataset using known dataset list.

        Raises:
            ValueError: If query dataset is not known.

        """

        if self.dataset != wildcard and self.dataset not in self.datasets:
            raise ValueError("Please specify a valid dataset.")

    def check(self, dataset):
        """Confirms whether a dataset should be downloaded in this session.

        Args:
            dataset (string): Dataset to scrape.

        Returns:
            bool: True if dataset should be downloaded, False if not.

        """

        return self.dataset == dataset or self.dataset == wildcard


class FilePatterns:
    """Reads and provides a list of file patterns to download via CL, input file.

        Attributes:
            file_pattern (string): File pattern to download.
            file_patterns_file (string): Location of file with list of file patterns to download.
            file_patterns (list): List of file patterns that can be downloaded.
    """

    def __init__(self, parse_args):
        """Reads in file pattern query from CL and input file.

        Args:
            parse_args (list): List of input CL arguments.

        """

        # sanitise target file_pattern on CL
        self.file_pattern = FilePatterns.get_file_pattern(parse_args)

        # check file_patterns file
        self.file_patterns_file = FilePatterns.get_file_pattern_file(
            parse_args)

        # read file_patterns file
        self.file_patterns = FilePatterns.get_file_patterns(
            self.file_patterns_file)

        # validate file_pattern
        self.validate()

    @staticmethod
    def get_file_pattern(parse_args):
        """Get query file pattern from CL.

        Args:
            parse_args (list): List of input CL arguments.

        Returns:
            string: Query file pattern.

        Raises:
            IOError: If no file pattern is provided on the CL.

        """

        if not parse_args.file_pattern:
            raise IOError("Please specify option file_pattern.")
        return parse_args.file_pattern

    @staticmethod
    def get_file_pattern_file(parse_args):
        """Gets input file from CL.

        Args:
            parse_args (list): List of input CL arguments.

        Returns:
            string: File patterns input file.

        Raises:
            IOError: If no input file is provided on the CL.

        """

        # check file_patterns file
        if not parse_args.file_patterns_file:
            raise IOError("Please specify option file_patterns_file.")
        return os.path.abspath(
            parse_args.file_patterns_file)

    @staticmethod
    def get_file_patterns(file_patterns_file):
        """Reads known file patterns from input file.

        Args:
            file_patterns_file (string): Location of file with list of file patterns to download.

        Returns:
            list: Known file patterns.

        """

        file_patterns = [line.rstrip('\n') for line in open(
            file_patterns_file)]
        print("got num_file_patterns: " + str(len(file_patterns)))
        return file_patterns

    def validate(self):
        """Sanity checks query file pattern using known file patterns.

        Raises:
            ValueError: If query file pattern is not known.

        """

        if self.file_pattern != wildcard and self.file_pattern not in self.file_patterns:
            raise ValueError("Please specify a valid file_pattern.")

    def check(self, file_pattern):
        """Confirms whether a sensor log should be downloaded in this session.

        Args:
            file_pattern (string): File pattern to download.

        Returns:
            bool: True if sensor log should be downloaded, False if not.

        """

        return self.file_pattern == file_pattern or self.file_pattern == wildcard


class Scraper:
    """Maintains login session and performs file requests.

            Attributes:
                username (string): RCD login username.
                password (string): RCD login password.
                session_requests (requests.Session): Persistent login session.
                dry_run (bool): Perform downloads (False) or check URLs (True)
    """

    def __init__(self, parse_args):
        """Sets up credentials and starts login session.

        Args:
            parse_args (list): List of input CL arguments.

        """

        # credentials
        self.username = Scraper.get_username(parse_args)
        self.password = Scraper.get_password(parse_args)
        self.dry_run = Scraper.get_dry_run(parse_args)

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

    @staticmethod
    def get_dry_run(parse_args):
        """Retrieves dry run config from CL.

        Args:
            parse_args (list): List of input CL arguments.

        Returns:
            bool: Perform downloads (False) or check URLs (True).

        Raises:
            IOError: If dry run is not provided on the CL.

        """

        return parse_args.dry_run

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

        # download file
        if not self.dry_run:
            # open local file
            print("downloading local_file_path: " + url_handler.local_file_path)
            file_handle = open(url_handler.local_file_path, 'wb')

            # iterate chunks
            for chunk in result.iter_content(
                    chunk_size=throttle.chunk_length):
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
                overwrite (bool): Overwrite pre-downloaded datasets?
                dataset (string): Dataset to download.
                dataset_dir (string): Dataset's download directory.
                tar_dir (string): Exctraction directory.
                tmp_dir (string): Temporary directory.
    """

    def __init__(self, parse_args, dataset):
        """Initialises local file paths for downloads concerning this dataset.

        Args:
            parse_args (list): List of input CL arguments.
            dataset (string): Dataset to download.

        """

        # root download dir
        self.downloads_dir = DatasetHandler.get_downloads_dir(parse_args)

        # should datasets be overwritten?
        self.overwrite = DatasetHandler.get_overwrite(parse_args)

        # dataset to download, or wildcard
        self.dataset = dataset

        # dataset download dir
        self.dataset_dir = os.path.join(self.downloads_dir, self.dataset)

        # tar extractions
        self.tar_dir = os.path.join(self.dataset_dir, self.dataset)

        # temporary holding dir
        self.tmp_dir = os.path.join(tmp_dir, self.dataset)

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

    @staticmethod
    def get_overwrite(parse_args):
        """Confirms overwrite behaviour using the CL.

        Args:
            parse_args (list): List of input CL arguments.

        Returns:
            bool: Overwrite behaviour.

        Raises:
            IOError: If overwrite was not provided on the CL.

        """

        if not parse_args.overwrite:
            raise IOError("Please specify option overwrite.")
        return parse_args.overwrite

    def check(self):
        """Checks dataset download directory and tries to overwrite if it exists.

        Raises:
            ValueError: If an existing dataset cannot be overwritten based on the CL and file system.

        """

        # confirm overwrite
        if not self.overwrite and os.path.exists(self.dataset_dir):
            raise ValueError(
                "dataset: " +
                dataset +
                " cannot be overwritten.")
        elif not self.overwrite and not os.path.exists(self.dataset_dir):
            print("creating dataset: " + dataset)
            os.mkdir(self.dataset_dir)
        elif self.overwrite and os.path.exists(self.dataset_dir):
            print("overwriting dataset: " + dataset)
            shutil.rmtree(self.dataset_dir)
            os.mkdir(self.dataset_dir)
        elif self.overwrite and not os.path.exists(self.dataset_dir):
            print("creating dataset: " + dataset)
            os.mkdir(self.dataset_dir)


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
            tar.extractall(path=self.dataset_handler.dataset_dir)

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
        if self.num_successful_unzipped != 0:
            # copy extracted contents to tmp
            shutil.copytree(
                self.dataset_handler.tar_dir,
                self.dataset_handler.tmp_dir)

            # delete root download
            shutil.rmtree(self.dataset_handler.dataset_dir)

            # move extracted files back to root download
            shutil.copytree(
                self.dataset_handler.tmp_dir,
                self.dataset_handler.dataset_dir)

            # clear tmp files
            shutil.rmtree(self.dataset_handler.tmp_dir)
        else:
            # no data was downloaded, remove empty folder
            shutil.rmtree(self.dataset_handler.dataset_dir)


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
            dataset_handler.dataset_dir, local_file_name)

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
        "--dry_run",
        action="store_true",
        help="Check file URLs only?")
    argument_parser.add_argument(
        "--dataset",
        dest="dataset",
        help="Dataset name from " + datasets_url + " e.g. " + dataset_example)
    argument_parser.add_argument(
        "--datasets_file",
        dest="datasets_file",
        help="List of dataset names from " +
             datasets_url + " - separated by new lines.")
    argument_parser.add_argument(
        "--file_pattern",
        dest="file_pattern",
        help="File pattern from " +
             datasets_url +
             " e.g. " +
             file_pattern_example)
    argument_parser.add_argument(
        "--file_patterns_file",
        dest="file_patterns_file",
        help="List of file patterns from " +
             datasets_url + " - separated by new lines.")
    argument_parser.add_argument(
        "--downloads_dir",
        dest="downloads_dir",
        default=downloads_dir_example,
        help="Root download directory e.g. " + downloads_dir_example)
    argument_parser.add_argument(
        "--overwrite",
        type=bool,
        default=True,
        help="Overwrite datasets already downloaded?")
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
    datasets = Datasets(parse_args)

    # set up file patterns file
    file_patterns = FilePatterns(parse_args)

    # persistent login
    scraper = Scraper(parse_args)

    # load cookies
    scraper.login()

    # start throttle
    throttle = Throttle(parse_args)

    # iterate datasets
    for dataset in datasets.datasets:
        # apply throttle
        throttle.wait()

        # check dataset
        if not datasets.check(dataset):
            continue

        # dataset handler
        dataset_handler = DatasetHandler(parse_args, dataset)

        # check overwrite
        if not scraper.dry_run:
            dataset_handler.check()

        # set up zipper
        zipper = Zipper(dataset_handler)

        # iterate file patterns
        for file_pattern in file_patterns.file_patterns:
            # check file pattern
            if not file_patterns.check(file_pattern):
                continue

            # set up URL handler
            url_handler = URLHandler(dataset_handler, file_pattern)

            # perform download
            file_was_found = scraper.scrape(url_handler)

            # unzip
            if file_was_found and not scraper.dry_run:
                zipper.unzip(url_handler)

        # tidy up
        if not scraper.dry_run:
            zipper.tidy_up()

    # console
    print("ScrapeMRGDatashare is finished!")
