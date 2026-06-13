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
script_name = os.path.basename(__file__)
source_cookie_name="crcns-data-source"

# dsid = "hc-2"


class Requester:
    # requests page or download file

    def __init__(self, new_data_source):
        self.cookie_jar = http.cookiejar.MozillaCookieJar(COOKIE_FILE)
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
        self.save_data_source(new_data_source)
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

    def save_data_source(self, new_data_source):
        """ data source is the server (AWS, NERSC, HPSS) to fetch the data from
        Currently not implemented on the server, but code added so in in the future
        data could be downloaded from multiple sources."""
        print(f"new_data_source={new_data_source}")
        if(new_data_source is None):
            # don't set the source if nothing specified
            return None
        previous_data_source = self.get_cookie_value(source_cookie_name, site_name)
        print(f"previous_data_source={previous_data_source}\n")
        if(previous_data_source != new_data_source):
            print(f"adding cookie name={source_cookie_name}, value={new_data_source}, site_name={site_name}\n")
            self.add_cookie(source_cookie_name, new_data_source, site_name)

    def save_cookies(self):
        """Saves current cookie state to disk."""
        self.cookie_jar.save(ignore_discard=True, ignore_expires=True)

    def get_cookie_value(self, cookie_name, domain):
        """Returns the value assigned to a cookie, or None"""
        for cookie in self.cookie_jar:
            if cookie.name == cookie_name and cookie.domain == domain:
                return cookie.value
        return None

    def add_cookie(self, name, value, domain, path='/', secure=False):
        """Add a custom cookie to the cookie jar."""
        cookie = http.cookiejar.Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain=domain,
            domain_specified=True,
            domain_initial_dot=domain.startswith('.'),
            path=path,
            path_specified=True,
            secure=secure,
            expires=None,        # None = session cookie
            discard=True,
            comment=None,
            comment_url=None,
            rest={}
        )
        self.cookie_jar.set_cookie(cookie)

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


class Login_crcns:

    def __init__(self, requester, dsid, username, password, logout):
        # requester - Requester object
        # dsid - dataset id, something like 'hc-3'
        # logout - true if user is requesting logging out
        self.requester = requester
        self.dsid = dsid
        self.username = username
        self.password = password
        if logout:
            self.do_logout()
        self.authorized = self.check_access(dsid)
        if self.authorized:
            self.method = "using previous session (saved cookie)"
        else:
            self.method = "by starting new session"
            # self.load_account_info()
            self.authorized = self.attempt_login()
            if self.authorized:
               self.authorized = self.check_access(dsid)
        if not self.authorized:
            sys.exit(f"Unable to login user '{username}' to {login_page} for dataset {dsid}.\n"
            f"Check file '{ACCOUNT_FILE}'.")
        
    def do_logout(self):
        url = logout_page
        html = self.requester.fetch_small(url)
        print("You are now logged out of CRCNS.org")
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
            # check for invalid dataset identifier
            match = re.search(r"Invalid data set identifier:\s+([^\s]*)", first_line)
            if match:
                html_dsid = match.group(1)
                id_unexpected = "" if html_dsid == dsid else f" (Unexpected: does not match entered id '{dsid}'"
                sys.exit(first_line + id_unexpected)
            # Logged in as jteeters (Jeff Teeters). logout.
            match = re.search(r"Logged in as\s+([^\s]+)\s+\(([^\)]*)\)", clean_text, re.IGNORECASE)
            if match:
                authorized = True
                self.html_returned_username = match.group(1)
                self.html_returned_full_name = match.group(2)
                # make sure logged in using username in file crcns-account.txt
                if self.html_returned_username != self.username:
                    sys.exit(f"** Changed username detected **\n"
                        f"Was loged in as user '{self.html_returned_username}'\n"
                        f"but file {ACCOUNT_FILE} specifies user '{self.username}'\n"
                        f"To correct, logout via 'python {script_name} --logout', then run command again")
            else:
                authorized = False
            # could extract username from cookie, but instead use username and full_name returned by match above
            # cookie_value = self.requester.get_cookie_value("__ac")
            # print(f"in check_access; cookie_value='{cookie_value}'\nclean_text=\n{clean_text}\n"
            #     f"first_line={first_line}\n"
            #     f"html_returned_username='{html_returned_username}', "
            #     f"html_returned_full_name='{html_returned_full_name}'")
        return authorized


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
        longest_name_width = max(len(str(item[0])) for item in self.filelist) + len(self.dsid)
        human_size_width = 10
        total_width = longest_name_width + human_size_width + 2  # two spaces between
        download_count=0
        total_bytes=0
        line_count=0
        print( "Would download files:" if step_show_info else "Downloading files:")
        print(f"{'Name':<{longest_name_width}}  {'Size':<{human_size_width}}")
        print("-"*total_width)
        for file_info in self.filelist:
            file_name, file_size, source = file_info
            full_path=f"{self.dsid}/{file_name}"
            size_human = format_bytes(file_size)
            print(f"{full_path:<{longest_name_width}}  {size_human:>{human_size_width}}", end="")
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
    Loads command line arguments and contents of crcns-account.txt file (username and password).
    Values loaded stored in instance variables:
      - dsid   - Dataset ID or None (if not specified on command line)
      - logout - set to True if command line argument -l or --logout specified
      - username - username loaded from file 'crcns-account.txt'
      - password - password loaded from file 'crcns-account.txt'
    """

    def __init__(self):
        self._parse_args()
        self._parse_account_file()
 

    def _parse_args(self):
        """Define and parse command-line arguments, seeding instance variables."""
        parser = argparse.ArgumentParser(
            description="Batch download data files from CRCNS.org.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=f"""
Example
  # specify dataset (example: 'pvc-1') on command line:
  python {script_name} pvc-1
""",
        )
        parser.add_argument(
            "dataset_id",
            nargs="?",
            default=None,
            help="ID of the dataset to download (examples: `pvc-1`, `hc-2`",
        )
        parser.add_argument(
            "--logout", "-l",
            action="store_true",
            help=f"Logout of CRCNS.org (so will start a new session on next run)",
        )

        parser.add_argument(
            "--source", "-s",
            type=str,
            help=f"Source of data.  Currently not used.  Placeholder for future implementation",
        )

        args = parser.parse_args()
        self.dsid = args.dataset_id
        self.logout = args.logout
        self.data_source = args.source
        # if logout specified don't require dsid
        if self.logout:
            return
        # make sure dsid provided
        if not self.dsid:
            self.dsid = self._prompt_until_given("Dataset ID (example 'pvc-1'): ")

    def _prompt_until_given(self, prompt):
        """Prompt repeatedly until the user enters a non-empty value."""
        while True:
            value = input(prompt).strip()
            if value:   # strip again to make sure password is not all spaces
                return value
            print(f"  Value cannot be empty. Please try again.")

    def _parse_account_file(self):
        """Load account information from ACCOUNT_FILE."""
        account_file = Path(ACCOUNT_FILE)
        if not account_file.exists():
            sys.exit(f"File '{ACCOUNT_FILE}' not found.\nAborting.")
        file_content = account_file.read_text(encoding="utf-8")
        pattern = r".*?\scrcns_username='(.*)'.*?\scrcns_password='(.*)'"
        match = re.search(pattern, file_content, re.DOTALL)
        if match:
            self.username = match.group(1)
            self.password = match.group(2)
            if not self.username or not self.password:
                sys.exit(f"Error: unable to find non-empty username and password in file '{ACCOUNT_FILE}'.\n"
                    f"Suggestion: edit file '{ACCOUNT_FILE}' to include your CRCNS.org account information.\n")
                sys.exit(1)
        else:
            sys.exit(f"Error: Unable to find:\n# username='<username>'\n"
                f"# password='<password>'\nin file '{ACCOUNT_FILE}.")


def main():
    ui = UserInputParser()
    requester = Requester(ui.data_source)
    login = Login_crcns(requester, ui.dsid, ui.username, ui.password, ui.logout)
    print(f"Username '{ui.username}' ({login.html_returned_full_name}) logged in {login.method}.")
    downloader = Dataset_downloader(requester, ui.dsid)
    print("all done")


main()


