# script to verify downloads from crcns.org using md5 hash

import hashlib
import sys
import os
import re

def get_md5_hash(filename):
    hash_md5 = hashlib.md5()
    # Open file in read-bytes mode
    with open(filename, "rb") as f:
        # Read the file in chunks of 8192 bytes (8 KB)
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)      
    return hash_md5.hexdigest()


def validate_files(dsid):
    checksum_file = "checksums.md5"
    checkssum_file_path = f"{dsid}/{checksum_file}"
    if not os.path.exists(checkssum_file_path):
        print(f"File '{checkssum_file_path}' not found.  Aborting.")
        sys.exit(1)
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
                print(f"Line {line_number} in file '{self.checkssum_file_path} "
                    "did not match expected pattern.  Expecting <md5_hash> <file_name>\n"
                    f"Line is:\n{line}\nAborting.")
                sys.exit(1)
            expected_hash = match.group(1)
            file_name = match.group(2)
            path=f"{dsid}/{file_name}"
            if not os.path.exists(path):
                # file not downloaded
                not_downloaded.append(file_name)
                continue
            found_hash = get_md5_hash(path)
            if found_hash == expected_hash:
                print(f"{path} validated.")
                valid_count += 1
            else:
                print(f"** HASH DOES NOT MATCH: {path}")
                error_count += 1
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

def main():
    dsid = get_dsid()
    validate_files(dsid)

main()
