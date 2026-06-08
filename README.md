# crcns-downloader

Batch downloader and validator for CRCNS.org

A pair of lightweight, zero-dependency Python command-line scripts to batch download datasets from the CRCNS.org repository and verify their integrity using MD5 checksums.

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ⚡ Zero Dependencies
These scripts rely entirely on the **Python Standard Library**. No `pip install`, virtual environments, or external packages are required. They work out of the box on Windows, macOS, and Linux.
---

## Zero Dependencies

These scripts rely entirely on the **Python Standard Library**. No `pip install`, virtual environments, or external packages are required. They work out of the box on Windows, macOS, and Linux.
---

## 📁 Repository Structure
* `downloader.py` — Initializes datasets and batch downloads files based on user selection.
* `validator.py` — Computes MD5 hashes of downloaded files and validates them against expected values.
* `crcns-account.txt` — Used to specify the username and password for the account on CRCNS.org used to download the files.
* `README.md` — Project documentation.
* `LICENSE` — Terms of use (MIT License).
---

## 🚀 How It Works (Step-by-Step)
Managing a dataset involves an initialization phase, a quick file configuration step, and the final download/validation execution.
### Step 1: Initialize the Dataset
Run the download script with your dataset ID. On this first run, the script will fetch the metadata files and then pause to let you choose your downloads.
```bash
python crcns-downloader.py YOUR_DATASET_ID
```

**What happens next:**
1. The script creates a local folder named after your dataset ID.
2. It downloads two configuration files into that folder: `filelist.txt` and `checksums.md5`.3. The script prints instructions to your terminal and exits.---
### Step 2: Select Your Files
Open the newly downloaded `filelist.txt` file in any text editor. By default, every file is listed with a leading space. 

You can control how files are selected by changing the **Mode** line at the top of the file, allowing you to make minimal edits depending on your needs.

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
Use this mode if you only want to download a **few** specific files from a large dataset.
* **To download a file:** Change the leading space to a `+` sign.
* **To skip a file:** Leave it as-is (with the leading space).
```text
# mode='+'
+data_file_01.csv   <-- Will be downloaded
 data_file_02.csv   <-- Will be SKIPPED
 data_file_03.csv   <-- Will be SKIPPED
```

*(Advanced: You can use multiple `# mode='...'` lines throughout the file to switch selection modes mid-list).*
---
### Step 3: Execute the DownloadRun the exact same command a second time. The script reads your customized `filelist.txt` and downloads your selected files.
```bash
python downloader.py YOUR_DATASET_ID
```
---
### Step 4: Verify Your Files (`validator.py`)
Once your downloads are complete, run the validation script with the same dataset ID. It reads the `checksums.md5` file and checks every downloaded file to guarantee nothing was corrupted.
```bash
python validator.py YOUR_DATASET_ID
```
---
## 🤝 Contributing
Contributions, bug reports, and feature suggestions are welcome! 1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).5. Open a Pull Request.
---## 📄 License
Distributed under the MIT License. See the `LICENSE` file in this repository for more details.



