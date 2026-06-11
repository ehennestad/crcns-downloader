#!/usr/bin/env python3
import argparse
import os
import http.cookiejar
import urllib.request
import urllib.error
import re
import math
import sys
import stat
import pprint
import getpass
from pathlib import Path

# Safely check if the user is running at least Python 3.8
if sys.version_info < (3, 8):
    print("Error: This script requires Python 3.8 or higher.", file=sys.stderr)
    print(f"Your current version is {sys.version.split()[0]}.", file=sys.stderr)
    sys.exit(1)


ACCOUNT_FILE="crcns-account.txt"
COOKIE_FILE = "session_cookies.txt"
INFILE="filelist.txt"
CHECKSUMS_FILE="checksums.md5"
site_name="crcns.org"
site_url=f"https://{site_name}"
apache_alias = "d"  # used to specify page (script) for downloading data
download_url_base = f"{site_url}/{apache_alias}/"
login_page=f"{site_url}/login_form"
logout_page=f"{site_url}/logout"
script_name = {os.path.basename(__file__)}

# dsid = "hc-2"


class Requester:
    # requests page or download file

    def __init__(self):
        self.cookie_jar = http.cookiejar.MozillaCookieJar(COOKIE_FILE)
        self.cookie_handler = urllib.request.HTTPCookieProcessor(self.cookie_jar)
        self.redirect_handler = urllib.request.HTTPRedirectHandler()
        # Create the UNIVERSAL opener
        self.opener = urllib.request.build_opener(self.cookie_handler, self.redirect_handler)
        # Mimic a standard Windows Chrome browser to sneak past basic bot firewalls
        self.opener.addheaders = [
            ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                ' AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        ]

    def fetch_small(self, url, form_vars=None):
        # fetch what should be a small response
        # if given, form_vars is a dictionary of key-value pairs used to make a post request
        if os.path.exists(COOKIE_FILE):
            try:
                # Load saved cookies, ignoring expired or session-only flags if needed
                self.cookie_jar.load(ignore_discard=True, ignore_expires=True)
                # print("Successfully loaded existing cookies.")
            except Exception as e:
                pass
                # print(f"Could not load cookie file: {e}")
        # else:
            # print("No saved cookies found. Starting a fresh session.")
        try:
            # 6. Make the request using the custom opener (instead of urllib.request.urlopen)
            post_data = urllib.parse.urlencode(form_vars).encode('utf-8') if form_vars else None
            with self.opener.open(url, data=post_data) as response:
                html = response.read().decode('utf-8')
                status_code = response.getcode()

            # 7. Save any new or updated cookies back to the disk
            self.save_cookies()
            # print("\nCookies have been updated and saved to disk.")

        except urllib.error.URLError as e:
            print(f"HTTP Request failed: {e.reason}")
        return (html, status_code)

    def save_cookies(self):
        """Saves current cookie state to disk."""
        self.cookie_jar.save(ignore_discard=True, ignore_expires=True)


    def download_large_file(self, url, output_filename):
        """ Streams large content to disk using Range headers and the same opener."""
        # add expected size?

        # --- THE DIRECTORY FIX ---
        # Extract the directory path from the filename string
        # e.g., 'folder/subfolder/file.txt' becomes 'folder/subfolder'
        directory = os.path.dirname(output_filename)
    
        # If a directory path was provided and it doesn't exist yet, create it
        if directory and not os.path.exists(directory):
            # exist_ok=True prevents crashes if another process creates it concurrently
            os.makedirs(directory, exist_ok=True) 
            print(f"Created missing directory structure: {directory}")
        # -------------------------

        downloaded_bytes = 0
        file_mode = 'wb'
        
        if os.path.exists(output_filename):
            downloaded_bytes = os.path.getsize(output_filename)
            if downloaded_bytes > 0:
                file_mode = 'ab'
                print(f"Resuming download from byte offset: {downloaded_bytes}")

        # Construct specific request to append the dynamic Range header
        req = urllib.request.Request(url)
        if downloaded_bytes > 0:
            req.add_header('Range', f'bytes={downloaded_bytes}-')

        try:
            with self.opener.open(req) as response:
                if response.status == 200 and downloaded_bytes > 0:
                    print("Server ignored Range header. Restarting full download.")
                    file_mode = 'wb'
                    downloaded_bytes = 0
                
                content_length = response.getheader('Content-Length')
                total_size = int(content_length) + downloaded_bytes if content_length else None
                
                chunk_size = 1024 * 1024 # 1MB chunk size
                with open(output_filename, file_mode) as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded_bytes += len(chunk)
                        
                        # Console log progress tracking
                        if total_size:
                            percent = (downloaded_bytes / total_size) * 100
                            sys.stdout.write(f"\rProgress: {percent:.2f}%")
                            sys.stdout.flush()

                self.save_cookies() # Ensure final download cookies are retained
                print(f"\n{output_filename} downloaded.")
                return True
                
        except urllib.error.URLError as e:
            print(f"\nLarge download encountered network error: {e.reason}")
            return False
"""
from pathlib import Path
output_file = Path("/some/path/file.txt")
output_file.parent.mkdir(exist_ok=True, parents=True)
output_file.write_text("some text")


with open(output_file, 'w') as file:
    file.write("some text")
"""

class Login_crcns:

    def __init__(self, requester, dsid, username, password):
        # requester - Requester object
        # dsid - dataset id, something like 'hc-3'
        self.requester = requester
        self.dsid = dsid
        self.username = username
        self.password = password
        self.authorized = self.check_access(dsid)
        if self.authorized:
            self.method = "already logged in (from cookie)"
        else:
            self.method = "new login"
            # self.load_account_info()
            self.authorized = self.attempt_login()
        if not self.authorized:
            print(f"Unable to login user '{username}' to {login_page}.  Check file '{ACCOUNT_FILE}' "
            " or other method used to specify the username and pasword.\nAborting.")
            sys.exit(0)
        

    def check_access(self, dsid):
        url = f"{download_url_base}/{dsid}"
        html, status_code = self.requester.fetch_small(url)
        clean_text = re.sub(r'<[^>]*>', '', html).lstrip()
        first_line = clean_text.splitlines()[0]
        match = re.search("Login Required", first_line, re.IGNORECASE)
        if match:
            # Found 'Login required'"
            authorized = False
        else:
            match = re.search("Logged in as", clean_text, re.IGNORECASE)
            if match:
                authorized = True
            else:
                authorized = False
        return authorized

    # def load_account_info(self):
    #     """Load account information from ACCOUNT_FILE."""
    #     if not os.path.exists(ACCOUNT_FILE):
    #         print(f"File '{ACCOUNT_FILE}' not found.  Aborting.")
    #         sys.exit(1)
    #     file_content = Path(ACCOUNT_FILE).read_text(encoding="utf-8")
    #     pattern = r".*?\scrcns_username='(.*)'.*?\scrcns_password='(.*)'"
    #     match = re.search(pattern, file_content, re.DOTALL)
    #     if match:
    #         self.username = match.group(1)
    #         self.password = match.group(2)
    #     if not self.username or not self.password:
    #         print(f"Unable to find non-empty username and password in file '{ACCOUNT_FILE}'.")
    #         print(f"Suggestion: edit file '{ACCOUNT_FILE}' to include your CRCNS.org account information.")
    #         print("Aborting.")
    #         sys.exit(1)

    def attempt_login(self):
        # following found from submitted request (viewed in crome developer tools):
        # came_from=https%3A%2F%2Fcrcns.org%2Fd%2Fhc-2%2Fec013.527%2F&form.submitted=1&
        # js_enabled=0&cookies_enabled=&login_name=&pwd_empty=0&__ac_name=jteeters&__ac_password=612crcZIZ&submit=Log+in
        form_vars = {
            "form.submitted":1,
            "js_enabled": 0,
            "pwd_empty" :0,
            "__ac_name": self.username,
            "__ac_password": self.password,
            "submit": "Log+in"
        }
        html, status_code = self.requester.fetch_small(login_page, form_vars)
        authorized = len(html) > 1000 and status_code == 200
        return authorized


class Dataset_downloader:

    def __init__(self, requester, dsid):
        # requester - Requester object
        # dsid - dataset id, something like 'hc-3'
        self.requester = requester
        self.dsid = dsid
        self.download_index()
        self.download_checksums()
        self.load_index()
        self.download_files("show-info")
        self.download_files("download")

    def download_index(self):
        self.index_file = f"{self.dsid}/{INFILE}"
        if os.path.exists(self.index_file):
            # index file already downloaded, continue downloading files
            return
        url = f"{download_url_base}/{self.index_file}"
        output_filename = self.index_file
        self.requester.download_large_file(url, output_filename)
        print("\n" + "="*50)
        print("ℹ️  DATASET INITIALIZED SUCCESSFULLY")
        print("="*50)
        print(f"1. Open the file: {self.index_file}\n"
            "2. Follow instructions at the top to edit the file and specify which files to download:\n"
            "   - With mode 'default' put a '#' in front of files to NOT be downloaded. "
            " (All the others WILL be downloaded.)\n"
            "   - With mode '+', put a '+' in front of files to downloaded. (The other files will NOT be downloaded.)\n"
            f"3. Run 'python downloader.py {self.dsid}' again to start.")
        print("="*50)
        # print(f"Just downloaded '{self.index_file}'.  Edit the file to indicate which files "
        #     "should be downloaded, then rerun this script in order to download those files")
        exit(0)

    def download_checksums(self):
        # download checksums file for use by verify utility
        checksums_file_path = f"{self.dsid}/{CHECKSUMS_FILE}"
        if os.path.exists(checksums_file_path):
            # file already downloaded
            return
        url = f"{download_url_base}/{checksums_file_path}"
        output_filename = checksums_file_path
        self.requester.download_large_file(url, output_filename)

    def load_index(self):
        if not os.path.exists(self.index_file):
            print(f"File '{self.index_file}' not found.  Aborting.")
            sys.exit(1)
        options = {"mode": ["default", "+"], "source": ["aws", "nersc", "hpss"]}
        specified = {"mode":None, "source":"aws"}  # updated by function check_for_specification
        line_number = 0
        self.filelist = []
        with open(self.index_file, 'r', encoding='utf-8') as file:
            for line in file:
                line_number += 1
                # line.strip() removes the trailing newline character (\n)
                # line = line.strip()
                first_char = line[0]
                if(first_char == "#"):
                    self.check_for_specification('mode', specified, options, line, line_number)
                    self.check_for_specification('source', specified, options, line, line_number)
                else:
                    if specified['mode'] is None:
                        print("mode must be specified before first file (line starting with space or +).\n"
                            "line {line_number} in file '{self.index_file}\nAborting.")
                        sys.exit(1)
                    if first_char == "+" or (first_char == " " and specified["mode"] == "default"):
                        # need to download this file
                        # line will be like:
                        # ec013.528/ec013.528.mpg.tar.gz    327392489 (312.2 MB)
                        file_line_pattern = r"^[ \+]\s*([^\ ]*)\s(\d+)(?:\s*\(([\.\d]+) (\w+)\))?"
                        match = re.search(file_line_pattern, line)
                        if match:
                            file_name = match.group(1)
                            file_size = int(match.group(2))
                            file_hsize = match.group(3)
                            file_hsize_unit = match.group(4)
                            # ignore file_hsize and file_hsize_unit because they might not be present
                            # set file_source to None if matches default (first entry in options["source"]), e.g. 'aws'
                            file_source = None if specified["source"] == options["source"][0] else specified["source"]
                            self.filelist.append([file_name, file_size, specified["source"]])
                        else:
                            print(f"Line {line_number} specifying file to download in file '{self.index_file} "
                                "did not match expected pattern.  Expecting <file_name> <size> [(<hsize> <hunit>)]\n"
                                f"Line is:\n{line}\nAborting.")
                            sys.exit(1)
                    elif not (first_char == "#" or (first_char == " " and specified["mode"] == "+")):
                        print(f"Invalid first character in file '{self.index_file}' line {line_number}.\n"
                            f"Expecting '#', '+' or ' ' (space). Found '{first_char}\nAborting.")
                        sys.exit(1)
        # print("found filelist:")
        # pprint.pprint(self.filelist)


    def check_for_specification(self, name, specified, options, line, line_number):
        # check for specification like:  mode='default' or source='HPSS'
        pattern = r"^#\s+" + name + r"\s*=\s*'([^']+)'"
        match = re.search(pattern, line)
        if match:
            new_value = match.group(1)
            if(new_value not in options[name]):
                print(f"Invalid {name} ('{new_value}')specified on line {line} in file {self.index_file}\n"
                    "Expecting one of (" + ", ".join(options[name]) + ")\nAborting.")
                sys.exit(1)
            specified[name] = new_value


    def download_files(self, step):
        # step 'show-info' displays info about what would be downloaded, but does not download
        # step 'download' downloads the files
        if step not in ["show-info", "download"]:
            print(f"invalid state in download_files: {step}")
            sys.exit(1)
        step_show_info = step == "show-info"
        step_download = not step_show_info
        if len(self.filelist) == 0:
            print("No files specified for downloading.\nAborting.")
            sys.exit(1)
        download_count=0
        total_bytes=0
        line_count=0
        print( "Would download files:" if step_show_info else "Downloading files:")
        print("Name\tSize")
        for file_info in self.filelist:
            file_name, file_size, source = file_info
            full_path=f"{self.dsid}/{file_name}"
            size_human = format_bytes(file_size)
            print(f"{full_path}\t{file_size} ({size_human})", end="")
            if os.path.exists(full_path):
                current_size = os.path.getsize(full_path)
                bytes_needed= file_size - current_size
                if bytes_needed == 0:
                    print (" - already downloaded.  Skipping")
                    continue
                if bytes_needed < 0:
                    print(f" - saved file is {current_size} bytes, which is larger than the file to "
                        f"download ({file_size} bytes.\nThis should not happen.\nAborting.")
                    sys.exit(1)
                print(f" - {current_size} bytes downloaded; resuming download for {bytes_needed} remaining.")
            else:
                print("")
                bytes_needed = file_size
            if step_download:
                url = f"{download_url_base}/{full_path}" + ("" if source is None else "&" + source)
                output_filename = full_path
                self.requester.download_large_file(url, output_filename)
            download_count += 1
            total_bytes += bytes_needed
        size_human = format_bytes(total_bytes)
        if step_show_info:
            print(f"Will download {download_count} files, total of {total_bytes} bytes ({size_human})")
            if total_bytes == 0:
                print("Nothing to download.  Exiting program.")
                sys.exit(0)
            prompt = "Proceed with download? (y/n): "
            valid_choices = ["y", "yes", "n", "no"]
            user_response = get_valid_input(prompt, valid_choices)
            if user_response not in ["y", "yes"]:
                print("All done.")
                exit(0)
        else:
            print(f"Done downloading {download_count} files, {total_bytes} bytes ({size_human})")


def format_bytes(size_in_bytes: int) -> str:
    if size_in_bytes == 0:
        return "0 B"
        
    # Define standard data units
    units = ("B", "KB", "MB", "GB", "TB", "PB", "EB")
    
    # Find the correct power index (e.g., 1024^0=B, 1024^1=KB, etc.)
    i = int(math.floor(math.log(size_in_bytes, 1024)))
    
    # Guard against index errors for extremely large numbers
    i = min(i, len(units) - 1)
    
    # Calculate the scaled size
    if i == 0:
        # less than 1k bytes, don't round
        scaled_size = size_in_bytes
    else:
        p = math.pow(1024, i)
        scaled_size = round(size_in_bytes / p, 2)
    
    return f"{scaled_size} {units[i]}"

def get_valid_input(prompt, valid_choices, case_sensitive=False):
    """
    Prompts the user for input until they provide a value from the valid_choices list.
    """
    # Standardize choices to lowercase if case insensitivity is preferred
    if not case_sensitive:
        valid_choices = [str(choice).lower() for choice in valid_choices]
        
    while True:
        user_input = input(prompt).strip()
        
        # Determine comparison format based on case sensitivity preference
        check_input = user_input if case_sensitive else user_input.lower()
        
        if check_input in valid_choices:
            return user_input  # Returns original entry preserving user's casing
            
        print(f"Invalid choice! Please choose from: {', '.join(map(str, valid_choices))}\n")


class UserInputParser:
    """
    Handles all argument parsing, and resolves repository credentials and
    dataset ID from multiple sources in priority order:
      1. Command-line arguments  (--username, --password, dataset_id)
      2. Environment variables   (REPO_USERNAME, REPO_PASSWORD)
      3. Config file             (default: crcns-account.txt)
      4. Interactive prompt
    """

    DEFAULT_CONFIG_FILE = Path("crcns-account.txt")
    ENV_USERNAME = "CRCNS_USERNAME"
    ENV_PASSWORD = "CRCNS_PASSWORD"

    def __init__(self):
        self.username = None
        self.password = None
        self.dataset_id = None
        self.config_file = self.DEFAULT_CONFIG_FILE
        self.parse_and_resolve()

    def parse_and_resolve(self):
        """
        Parse command-line arguments, then resolve all inputs (credentials
        and dataset ID) using the priority chain.  Returns self for chaining.
        """
        self._parse_args()
        if self.logout:
            # don't require other parameters if logging out
            return
        self._apply_env_vars()
        self._apply_account_file()
        self._prompt_if_missing()
        return self

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_args(self):
        """Define and parse command-line arguments, seeding instance variables."""
        parser = argparse.ArgumentParser(
            description="Batch download data files from CRCNS.org.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=f"""
Credential resolution order (highest to lowest priority):
  1. --username / --password flags
  2. CRCNS_USERNAME / CRCNS_PASSWORD environment variables
  3. account-info.ini config file
  4. Interactive prompt

Examples:
  # Use config file for credentials, specify dataset (example: 'pvc-1') on command line:
  python {script_name} pvc-1

  # Specify username on command line, get prompted for password:
  python {script_name} --username myname pvc-1

  # Fully non-interactive (e.g. for automation):
  python {script_name} --username myname --password secret pvc-1
  CRCNS_USERNAME=myname CRCNS_PASSWORD=secret python {script_name} pvc-1
            """,
        )
        parser.add_argument(
            "dataset_id",
            nargs="?",
            default=None,
            help="ID of the dataset to download (examples: `pvc-1`, `hc-2`",
        )
        parser.add_argument(
            "--username", "-u",
            help="CRCNS.org username (overrides config file and env var)",
        )
        parser.add_argument(
            "--password", "-p",
            help="CRCNS.org password (if omitted, will prompt securely)",
        )
        parser.add_argument(
            "--config", "-c",
            default=None,
            help=f"Path to credentials config file (default: {self.DEFAULT_CONFIG_FILE})",
        )

        parser.add_argument(
            "--logout", "-l",
            action="store_true",
            help=f"Logout of CRCNS.org (so will start a new session on next run)",
        )

        args = parser.parse_args()
        self.logout = args.logout
        self.username = args.username
        self.password = args.password
        self.dataset_id = args.dataset_id
        account_file = args.config if args.config else ACCOUNT_FILE
        self.account_file = Path(account_file)

    def _apply_env_vars(self):
        """Fill any missing credentials from environment variables."""
        if not self.username:
            self.username = os.environ.get(self.ENV_USERNAME)
        if not self.password:
            self.password = os.environ.get(self.ENV_PASSWORD)

    def _apply_account_file(self):
        """Fill any missing credentials from the ACCOUNT_FILE file."""
        if self.username and self.password:
            return  # nothing to do

        if not self.account_file.exists():
            return

        # self._check_file_permissions()  # don't bother with this

        """Load account information from ACCOUNT_FILE."""
        file_content = self.account_file.read_text(encoding="utf-8")
        pattern = r".*?\scrcns_username='(.*)'.*?\scrcns_password='(.*)'"
        match = re.search(pattern, file_content, re.DOTALL)
        if match:
            username = match.group(1)
            password = match.group(2)
            if not username or not password:
                print(f"Unable to find non-empty username and password in file '{ACCOUNT_FILE}'.\n"
                    f"Suggestion: edit file '{ACCOUNT_FILE}' to include your CRCNS.org account information.\n"
                    "Aborting.")
                sys.exit(1)
            if not self.username:
                self.username = username
            if not self.password:
                self.password = password

    def _prompt_until_given(self, prompt, password=False):
        """Prompt repeatedly until the user enters a non-empty value."""
        while True:
            value = input(prompt).strip() if not password else getpass.getpass(prompt)
            if value.strip():   # strip again to make sure password is not all spaces
                return value
            print(f"  {prompt.strip()} cannot be empty. Please try again.")

    def _prompt_if_missing(self):
        """Interactively prompt for any inputs that are still missing."""
        if not self.username:
            self.username = self._prompt_until_given("Username: ")
        if not self.password:
            self.password = self._prompt_until_given("Password: ", password=True)  # input is hidden
        if not self.dataset_id:
            self.dataset_id = self._prompt_until_given("Dataset ID (example 'pvc-1'): ")

    def _check_file_permissions(self):
        """Warn if the config file is readable by group or others."""
        mode = self.config_file.stat().st_mode
        if mode & stat.S_IRGRP or mode & stat.S_IROTH:
            print(
                f"Warning: {self.config_file} is readable by others. "
                f"Run: chmod 600 {self.config_file}"
            )

def do_logout(requester):
    url = logout_page
    html = requester.fetch_small(url)
    print("You are now logged out of CRCNS.org")
    sys.exit(1)


"""
import argparse
import sys

def get_dataset_id():
    parser = argparse.ArgumentParser(
        description="Batch download files from a data repository." # Change text for validator script
    )
    
    # Define a positional argument that is optional (nargs='?')
    parser.add_argument(
        'dataset_id', 
        nargs='?', 
        help="The unique ID of the dataset to process"
    )
    
    args = parser.parse_args()
    
    # If the user didn't provide the argument, prompt them interactively
    if args.dataset_id is None:
        try:
            args.dataset_id = input("Enter the dataset ID: ").strip()
            if not args.dataset_id:
                print("Error: Dataset ID cannot be empty.", file=sys.stderr)
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
            sys.exit(1)
            
    return args.dataset_id

# Usage
dataset_id = get_dataset_id()
print(file=sys.stderr, text=f"Processing dataset: {dataset_id}")

def get_dsid():
    if len(sys.argv) > 2:
        print(f"Usage: {os.path.basename(__file__)} [dataset-id]");
        sys.exit(1)
    if len(sys.argv) == 2:
        dsid = sys.argv[1]
    else:
        while True:
            dsid = input("Enter dataset ID (example 'pvc-1': ").strip()
            if dsid != "":
                break
    print ("Downloading for dataset '{dsid}")
    return dsid
"""


def main():
    ui = UserInputParser()
    requester = Requester()
    if ui.logout:
        do_logout(requester)
    login = Login_crcns(requester, ui.dataset_id, ui.username, ui.password)
    if not login.authorized:
        print(f"Unable to login to {login_page}.  Check file '{ACCOUNT_FILE} "
            " to be sure it has the correct values for your {} account.")
    status_message = f"Username '{ui.username}' logged in" if login.authorized else "Login NOT authorized"
    method_message = login.method
    print(f"{status_message}. Method: {method_message}.")
    downloader = Dataset_downloader(requester, ui.dataset_id)
    print("all done")


main()

"""

# 1. Define the cookie storage file path
COOKIE_FILE = "session_cookies.txt"

# 2. Initialize a Mozilla-compatible cookie jar
cookie_jar = http.cookiejar.MozillaCookieJar(COOKIE_FILE)

# 3. Check if a cookie file already exists from a previous request
if os.path.exists(COOKIE_FILE):
    try:
        # Load saved cookies, ignoring expired or session-only flags if needed
        cookie_jar.load(ignore_discard=True, ignore_expires=True)
        print("Successfully loaded existing cookies.")
    except Exception as e:
        print(f"Could not load cookie file: {e}")
else:
    print("No saved cookies found. Starting a fresh session.")

# 4. Create a custom URL opener that manages the cookie jar automatically
cookie_handler = urllib.request.HTTPCookieProcessor(cookie_jar)
opener = urllib.request.build_opener(cookie_handler)

# --- THE FIX: Create a Cookie handler AND a Browser Header injector ---
# Mimic a standard Windows Chrome browser to sneak past basic bot firewalls
opener.addheaders = [
    ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
]

# 5. Define your target URL
url = f"{site_url}/{apache_alias}/{dsid}"

try:
    print(f"Sending request to: {url}")
    
    # 6. Make the request using the custom opener (instead of urllib.request.urlopen)
    with opener.open(url) as response:
        html = response.read().decode('utf-8')
        print("\n--- Response Content ---")
        print(html)
        clean_text = re.sub(r'<[^>]*>', '', html).lstrip()
        first_line = clean_text.splitlines()[0]
        print (f"first_line='{first_line}'")
        pattern = "Login Required"
        match = re.search(pattern, first_line, re.IGNORECASE)
        if match:
            print("Found 'Login required'")


    # 7. Save any new or updated cookies back to the disk
    cookie_jar.save(ignore_discard=True, ignore_expires=True)
    print("\nCookies have been updated and saved to disk.")

except urllib.error.URLError as e:
    print(f"HTTP Request failed: {e.reason}")
"""
