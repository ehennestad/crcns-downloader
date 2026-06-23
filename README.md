# crcns-downloader
Batch downloader and validator for CRCNS.org
A pair of lightweight Python command-line scripts to batch download files from the CRCNS.org repository and verify their integrity using MD5 checksums.

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ⚡ Minimal Dependencies

These scripts rely primarily on the **Python Standard Library** and work out of the box on macOS and Linux with no additional packages required.

**Windows users may need one optional package:** On some Windows installations (particularly fresh installs or virtual machines), Python's built-in SSL certificate store may be incomplete, causing HTTPS connections to fail. If you see a certificate-related error, install `certifi`:

```bash
python -m pip install certifi
```

The scripts automatically detect and use `certifi` when it is present, and fall back to system SSL defaults otherwise. Installing `certifi` is harmless on any platform and may also be useful as a precaution on Windows.

---




# crcns-downloader

Batch downloader and validator for CRCNS.org

A pair of lightweight, zero-dependency Python command-line scripts to batch download files from the CRCNS.org repository and verify their integrity using MD5 checksums.

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ⚡ Zero Dependencies
* These scripts rely entirely on the **Python Standard Library**. No `pip install`, virtual environments, or external packages are required. They work out of the box on Windows, macOS, and Linux.
---

## 📁 Repository Structure
* `crcns-download.py` — Initializes datasets and batch downloads files based on user selection.
* `crcns-validate.py` — Computes MD5 hashes of downloaded files and validates them against expected values.
* `crcns-account-template.txt` — A template used to create file `crcns-account.txt` which stores the account information for the CRCNS.org account used to download the files.  If you don't have an account you can [create one for free](https://crcns.org/register).

* `README.md` — Project documentation.
* `LICENSE` — Terms of use (MIT License).
---

## 🚀 Initial Setup
Rename (or copy) file `crcns-account-template.txt` to `crcns-account.txt` and then edit that file to specify the username and password for the account at CRCNS.org used to download the data.  If you don't have an account use the above link to create one for free.


## 🚀 How to use the scripts (Step-by-Step)
Downloading and verifying the files in a dataset involves an initialization phase, a quick file configuration step, and the final download/validation execution.
### Step 1: Initialize the Dataset
Run the download script and specify a dataset ID. On this first run, the script will fetch the metadata files and then pause to let you choose which files to download.
```bash
python crcns-downloader.py DATASET_ID
```
Where DATASET_ID is the ID for the dataset at CRCNS.org (for example, `pvc-1` or `hc-2`).

**What happens next:**
1. The script creates a local folder named the DATASET_ID.
2. It downloads two configuration files into that folder: `filelist.txt` and `checksums.md5`.3. The script prints instructions to your terminal and exits.
---
### Step 2: Select Your Files
Open the newly downloaded `filelist.txt` file in any text editor. By default, every file is listed with a leading space. 

You can control how files are selected by changing the **Mode** line near the top of the file, allowing you to make minimal edits depending on your needs.

#### Option A: Default Mode (`# mode='default'`)
Use this mode if you want to download **most** files in the dataset.
* **To download a file:** Leave it as-is (with the leading space).
* **To skip a file:** Change the leading space to a `#` to comment it out.
```text
# mode='default'
 data_file_01.csv   <-- Will be downloaded
#data_file_02.csv   <-- Will be SKIPPED
 data_file_03.csv   <-- Will be downloaded
```

#### Option B: Selection Mode (`# mode='+'`)
Use this mode if you only want to download a **few** specific files from a dataset containing many files.
* **To download a file:** Change the leading space to a `+` sign.
* **To skip a file:** Leave it as-is (with the leading space).
```text
# mode='+'
+data_file_01.csv   <-- Will be downloaded
 data_file_02.csv   <-- Will be SKIPPED
 data_file_03.csv   <-- Will be SKIPPED
```

* *(Advanced: You can use multiple `# mode='...'` lines throughout the file to switch selection modes mid-list.)*
---
### Step 3: Execute the Download
Run the exact same command a second time. The script reads your customized `filelist.txt` and displays the list of files to be downloaded and the total size and prompts you to confirm to proceed.  If you conferm, the script downloads your selected files.
```bash
python downloader.py DATASET_ID
```
---
### Step 4: Verify Your Files (`validator.py`)
Once your downloads are complete, run the validation script with the same dataset ID. It reads the `checksums.md5` file and checks every downloaded file to guarantee nothing was corrupted.
```bash
python validator.py DATASET_ID
```
---
## 🤝 Contributing
Contributions, bug reports, and feature suggestions are welcome! 1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).5. Open a Pull Request.
---## 📄 License
Distributed under the MIT License. See the `LICENSE` file in this repository for more details.


## Details about alternate ways of specifying account information

The script supports three ways to supply your username and password. Choose whichever suits your workflow. If credentials are provided through more than one method, see [Credential Resolution Order](#credential-resolution-order) for which takes precedence.

---

### Option 1: `crcns-account.txt` File (Recommended for Regular Use)

This option was [described above](#initial-setup).


> **Security:** On macOS/Linux, restrict the file so only you can read it:
> ```bash
> chmod 600 crcns-account.ini
> ```
> The script will warn you if the file is readable by other users on the system.

> **Note:** `account-info.ini` is listed in `.gitignore` and will not be committed to the repository. Never commit your credentials.

---

### Option 2: Environment Variables

Set the following environment variables before running the script:

| Variable         | Description        |
|------------------|--------------------|
| `REPO_USERNAME`  | Your username      |
| `REPO_PASSWORD`  | Your password      |

**Setting them for a single run:**

```bash
REPO_USERNAME=myname REPO_PASSWORD=mysecret python download.py DATASET123
```

**Setting them for the current shell session:**

```bash
export REPO_USERNAME=myname
export REPO_PASSWORD=mysecret
python download.py DATASET123
```

**In a CI/CD pipeline**, set these as secret environment variables in your pipeline configuration (e.g. GitHub Actions Secrets, GitLab CI Variables).

---

### Option 3: Command-Line Arguments

Pass credentials directly as flags. This is useful for one-off runs or testing.

Specify both username and password:

```bash
python download.py --username myname --password mysecret DATASET123
```

Specify only the username; the script will prompt for the password securely (input is hidden):

```bash
python download.py --username myname DATASET123
Password:
```

> **Note:** Passing `--password` on the command line may expose your password in your shell history. When possible, omit `--password` and let the script prompt you for it.

---


## Credential Resolution Order

When credentials are available from more than one source, the script uses the following priority order (highest to lowest):

| Priority | Source                        |
|----------|-------------------------------|
| 1        | `--username` / `--password` command-line flags |
| 2        | `REPO_USERNAME` / `REPO_PASSWORD` environment variables |
| 3        | `account-info.ini` config file |
| 4        | Interactive prompt             |

This means, for example, that setting `--username` on the command line will override the username in your config file, while still using the password from the config file.

---

## Security Notes

- **Never commit credentials** to version control. The `account-info.ini` file is included in `.gitignore` for this reason.
- **Use `chmod 600 account-info.ini`** on macOS/Linux to ensure only your user account can read the file.
- **Avoid `--password` in shell commands** that will be logged in your shell history. Use the interactive prompt or environment variables instead.
- For automated pipelines, use your platform's secrets management (GitHub Actions Secrets, environment variable injection, etc.) rather than storing credentials in files.


