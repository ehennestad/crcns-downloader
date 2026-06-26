#!/usr/bin/env python3

# script to verify downloads from crcns.org using md5 hash

import argparse
import hashlib
import sys
import os
import re
from pathlib import Path
from pathlib import PurePath

CHECKSUMS_FILE="checksums.md5"
script_name = os.path.basename(__file__)

def get_md5_hash(filename):
    hash_md5 = hashlib.md5()
    # Open file in read-bytes mode
    with open(filename, "rb") as f:
        # Read the file in chunks of 8192 bytes (8 KB)
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)      
    return hash_md5.hexdigest()


def validate_files(dsid, output_dir, patterns):
    # checksum_file = "checksums.md5"
    checkssum_file_path = output_dir / dsid / CHECKSUMS_FILE
    if not os.path.exists(checkssum_file_path):
        print(f"File '{checkssum_file_path}' not found.  Aborting.")
        sys.exit(1)
    # if pattern specified, make a set containing all files matching the pattern
    pattern_file_set = get_pattern_file_set(dsid, checkssum_file_path, patterns) if patterns is not None else None
    file_count=0
    valid_count=0
    error_count=0
    line_number=0
    not_downloaded = []  # names of files not downloaded
    # line in file will be like:
    # eb5053b61c8d32df777f6cfd2b6db06d  docs/crcns-hc2-processing-flowchart.pdf
    line_pattern = r"([^\s]+)\s+(.+?)\s*$"  # will allow spaces in file name (but normally should not occur)
    with open(checkssum_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line_number += 1
            match = re.search(line_pattern, line)
            if not match:
                sys.exit(f"Line {line_number} in file '{checkssum_file_path} "
                    "did not match expected pattern.  Expecting <md5_hash> <file_name>\n"
                    f"Line is:\n{line}\nAborting.")
            expected_hash = match.group(1)
            file_name = match.group(2)
            if pattern_file_set and file_name not in pattern_file_set:
                # this file does not match any of the specified patterns
                continue
            file_path= output_dir / dsid / file_name
            if not os.path.exists(file_path):
                # file not downloaded
                not_downloaded.append(f"{file_path}")
                continue
            found_hash = get_md5_hash(file_path)
            if found_hash == expected_hash:
                print(f"{file_path} validated.")
                valid_count += 1
            else:
                print(f"** HASH DOES NOT MATCH: {file_path}")
                error_count += 1
            file_count += 1
    print(f"Processed {file_count} files.")
    print(f"Number validated={valid_count}.  Number hash not matching={error_count}.")
    num_not_downloaded = len(not_downloaded)
    print(f"{num_not_downloaded} files not yet downoaded.", end="")
    not_downloaded_file_list = "\n".join(not_downloaded)
    if num_not_downloaded < 10:
        print(f"They are:\n{not_downloaded_file_list}")
    else:
        prompt = "\nList files not yet download? (y/n): "
        valid_choices = ["y", "yes", "n", "no"]
        user_response = get_valid_input(prompt, valid_choices)
        if user_response in ["y", "yes"]:
            print(f"Files not yet downloaded:\n{not_downloaded_file_list}")
    print("All done.")

def get_pattern_file_set(dsid, checkssum_file_path, patterns):
    # returns a set that contains all the files that match a
    # pattern specified on the command line
    # first, get list of filenames from checksum file
    # make list of file_name only in txt file
    files_in_txt_file_name_only = []
    line_pattern = r"([^\s]+)\s+(.+?)\s*$"  # will allow spaces in file name (but normally should not occur)
    with open(checkssum_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            match = re.search(line_pattern, line)
            if not match:
                sys.exit(f"Line {line_number} in file '{self.checkssum_file_path} "
                    "did not match expected pattern.  Expecting <md5_hash> <file_name>\n"
                    f"Line is:\n{line}\nAborting.")
            file_name = match.group(2)
            files_in_txt_file_name_only.append(file_name)
    # now iterate through cmd line list of patterns (--patterns option)
    # for each pattern, find the files_in_text that match, and set "found" flag to True
    pattern_file_set = set()
    patterns_not_matching_any_files = []
    for glob_pattern in patterns:
        glob_pattern = glob_pattern.lstrip('/')  # remove any leading slash
        matching_files = [f for f in files_in_txt_file_name_only if PurePath(f).match(glob_pattern)]
        if (not matching_files):
            patterns_not_matching_any_files.append(glob_pattern)
        else:
            # add matching files to set
            pattern_file_set.update(matching_files)
    if(patterns_not_matching_any_files):
        print("WARNING: The following patterns (specified with the --patterns option) "
            f"didn't match any files in dataset '{dsid}':")
        print("\n".join(sorted(patterns_not_matching_any_files)))
    return pattern_file_set


def get_dsid_not_used():
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
    print ("Validating files in dataset '{dsid}")
    return dsid


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
    Values loaded stored in instance variables:
      - dsid   - Dataset ID (if not specified on command line will prompt user to enter)
      - output_dir - base directory to create dataset id's inside.  Default is current working directory
      - file_list - list of files to download.  If not specified 
    """

    def __init__(self, dataset_id_required = True):
        self.dataset_id_required = dataset_id_required
        self._parse_args()
        # self._display_values()
        # sys.exit("done for now")
 

    def _extract_leading_dataset_id(self, argv):
        """
        If argv's first token doesn't look like a flag, treat it as the
        dataset id and remove it from argv. Returns (dataset_id_or_None, remaining_argv).
        """
        if argv and not argv[0].startswith("-"):
            return argv[0], argv[1:]
        return None, argv


    def _parse_args(self):
        """Define and parse command-line arguments, seeding instance variables."""

        dataset_id = "dataset_id"
        id_description = "dataset_id        ID for the dataset to download (e.g. 'pvc-1')."
        usage = (f"%(prog)s dataset_id [-h] [-d OUTPUT_DIR] [-p PATTERN [PATTERN ...]]")

        parser = argparse.ArgumentParser(
            description="Verify files downloaded from CRCNS.org.",
            usage=usage,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=(
                "Example\n"
                "  # specify dataset (example: 'pvc-1') on command line:\n"
                f"  python {script_name} pvc-1"),
            )

        # Manually document dataset_id in its own group so it appears at the top
        positional_group = parser.add_argument_group("positional arguments")
        positional_group.description = id_description
        # _action_groups order at this point:
        #   [0] default "positional arguments" (empty, we're not using it)
        #   [1] default "optional arguments"
        #   [2] our custom group  <-- we want this at index 1
        parser._action_groups.insert(1, parser._action_groups.pop(-1))

        # Not positional -- we fill this in ourselves from the leading token.
        # suppress so it doesn't show up twice in the auto-generated options list.
        parser.add_argument("--id", dest="dataset_id", default=None, help=argparse.SUPPRESS)

        parser.add_argument(
            "-d", "--dir",
            type=Path,
            default="",  # Path.cwd(), empty for current working directory
            dest="output_dir",
            help=(
                "Directory in which the dataset's base directory (for example, 'pvc-1') is located. "
                "Defaults to the current working directory."
            ),
        )

        parser.add_argument(
            "-f", "--files",
            nargs="+",
            metavar="PATH",
            help=(
                "One or more specific files to verify, given as paths relative "
                "to the dataset root (e.g. docs/readme.txt). If omitted, the file "
                f"list is read from the datasets '{CHECKSUMS_FILE}' file."
            ),
        )

        parser.add_argument(
            "-p", "--patterns",
            nargs="+",
            metavar="PATTERN",
            help=("One or more glob patterns specifying files to verify, "
                    "given relative to the dataset root. Patterns may include "
                    "wildcards, e.g. 'docs/*' for all files in a directory or "
                    "'**/*.pdf' for all PDF files regardless of location. If "
                    "omitted, all downloaded files in the dataset are verified."
            ),
        )


        argv = sys.argv[1:]
        leading_id, rest = self._extract_leading_dataset_id(argv)
        args = parser.parse_args(rest)


        if leading_id is not None:
            args.dataset_id = leading_id

        if not args.dataset_id:
            if self.dataset_id_required:
                parser.error("dataset_id is required")
            else:
                args.dataset_id = self._prompt_until_given("Dataset ID (example 'pvc-1'): ")

        self.dsid = args.dataset_id
        self.output_dir = args.output_dir
        if(not self.output_dir.is_dir()):
            sys.exit(f"Error: Specified output directory '{self.output_dir}' does not exist or is a file.")
        self.patterns = args.patterns


    def _display_values(self):
        print(f"dsid='{self.dsid}'")
        print(f"output_dir='{self.output_dir}'")
        print(f"patterns='{self.patterns}'")


    def _prompt_until_given(self, prompt):
        """Prompt repeatedly until the user enters a non-empty value."""
        while True:
            value = input(prompt).strip()
            if value:   # strip again to make sure password is not all spaces
                return value
            print(f"  Value cannot be empty. Please try again.")


def main():
    ui = UserInputParser()
    validate_files(ui.dsid, ui.output_dir, ui.patterns)

main()
