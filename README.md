# Media Duplicate Finder

This collection of Python scripts helps you find and group **duplicate or near‑duplicate** images and videos by comparing their visual content rather than file names or binary hashes. Three variants of perceptual hashing are provided:

* **dHash** (Difference Hash)
* **pHash** (Perceptual Hash using DCT)
* **wHash** (Wavelet Hash)

Each variant follows the same interface and workflow—choose the one that best fits your data and performance needs.

---

## Table of Contents

1. [Overview](#overview)
2. [Variants](#script-variants)
3. [Configuration](#configuration-highlights)
4. [Installation](#installation)
5. [Usage](#usage)
6. [License](#license)

---

## Overview

This tool scans an `input/` directory, computes perceptual hashes for images or video frames, groups similar files by Hamming distance, and moves each group into its own folder under `output/`.

> **Note:** On each script run, any files previously grouped in `output/` will be moved back into `input/` to prevent accidental data loss and ensure a consistent reprocessing loop.

## Script Variants

### dHash (Difference Hash)

* **Algorithm**: resize to `(HASH_SIZE+1)×HASH_SIZE`, compare each pixel to its right neighbor.
* **Speed**: very fast (pixel‑level ops only).
* **Best for**: exact or near‑exact duplicates, minor brightness/contrast changes.
* **Limitations**: sensitive to rotations, crops, perspective shifts.

### pHash (Perceptual Hash)

* **Algorithm**: apply 2D DCT to a small grayscale image, threshold low‑frequency coefficients against the mean.
* **Speed**: moderate (incurs DCT computation).
* **Best for**: robust matching under compression artifacts, small rotations, resizes, color shifts.
* **Limitations**: heavier CPU cost, may confuse images with similar global structure.

### wHash (Wavelet Hash)

* **Algorithm**: perform a Haar wavelet transform, capture horizontal/vertical detail coefficients.
* **Speed**: similar to pHash (wavelet transform cost).
* **Best for**: edge‑ and texture‑sensitive comparisons, slightly more robust to fine details than pHash.
* **Limitations**: similar CPU cost to pHash, marginal gains in some cases.

---

## Configuration Highlights

* **MAX\_WORKERS**: number of parallel hashing processes (default: CPU cores up to 10).
* **CHUNK\_COEF**: controls batch size per worker; lower values → larger chunks (less overhead), higher values → smaller chunks (better load balancing).
* **MODE**: `image` or `video`.
* **FRAMES\_TO\_SAMPLE**: number of frames per video to hash (default: 20).
* **HASH\_SIZE**: dimension of the hash algorithm (e.g. 8 for dHash/wHash, 16 for pHash).
* **SIMILARITY\_THRESHOLD**: maximum Hamming distance for grouping (tune based on hash length).

---

## Installation

1. **Create a Virtual Environment:**
   python3.11 -m venv venv

2. **Enter the Virtual Enviroment:**
   source venv/bin/activate   # Linux/macOS

3. **Install Dependencies:**
   pip install -r requirements.txt

4. **Make the launcher executable (Linux/macOS only):**
   chmod +x run.sh

---

## Usage

Use the `run.sh` launcher to run any of the three hashing scripts or reset the workspace.

./run.sh [dhash|phash|whash|reset|help] [image|video] [KEY=VALUE]...

### Modes

* `dhash`   : Difference hash (fast, near-identical images)
* `phash`   : Perceptual hash (DCT-based, robust to transforms)
* `whash`   : Wavelet hash (texture/edge-sensitive)
* `reset`   : Move files from `output/` back into `input/`
* `help`    : Show this help message (default)

### Media Types

* `image` : Process still images ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
* `video` : Sample frames from videos ('.mp4', '.avi', '.mov', '.mkv', '.m4v')

### Override Defaults with `KEY=VALUE`

* `M_WORKERS=#`    : Max parallel workers (↑ speed, ↓ overhead)
* `C_CHUNK=#`      : Chunk coefficient (↑ batches, ↑ precision, ↓ speed)
* `S_FRAMES=#`     : Frames to sample per video (↑ precision, ↓ speed)
* `S_HASH=#`       : Hash size (↑ detail, ↓ speed)
* `S_THRESH=#`     : Similarity threshold (↑ grouping len, ↓ precision)
* `D_RUN=true`     : Dry-run: simulate moves without executing

### Examples

* #### Run pHash on images using 4 workers and a stricter threshold
  ./run.sh phash image M_WORKERS=4 S_THRESH=8
* #### Sample 30 frames for video dHash, no actual moves (dry run)
  ./run.sh dhash video S_FRAMES=30 D_RUN=true
* #### Reset workspace
  ./run.sh reset

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
