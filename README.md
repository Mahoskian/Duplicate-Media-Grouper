# MediaHashCluster

**MediaHashCluster** is a powerful perceptual hashing toolset for identifying and grouping visually similar media — including **duplicate**, **near-duplicate**, or even **vibe-aligned** images and videos.

Instead of relying on filenames or exact file hashes, this tool analyzes visual content using perceptual hashing to detect similarity based on structure, color, texture, and composition.

Three hash strategies are provided, each optimized for different types of similarity:

- 🔹 **dHash** — Fast and lightweight; great for detecting nearly identical files
- 🔹 **pHash** — DCT-based; ideal for grouping by overall visual content or “vibe”
- 🔹 **wHash** — Wavelet-based; more sensitive to texture and detail changes

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

- Scans your `input/` folder for images or videos
- Computes perceptual hashes for each file (or video frame sample)
- Compares files using Hamming distance
- Groups similar media into folders in `output/`
- **Note:** Resets grouped files to `input/` on each run to ensure clean, repeatable processing that avoids any potential loss in data.

> Whether you're de-duplicating your media dataset or curating by "similiar-style", **MediaHashCluster** helps you organize large volumes of visual media with perceptual intelligence.

> **OS Compatibility:** This repo is currently configured for Linux. It can also run on macOS or Windows, but may require additional setup by the user.

---

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

Each configuration option balances speed, accuracy, and perceptual sensitivity. Adjust these based on whether you're targeting exact duplicates, light edits, or vibe-level similarity.

* **MAX\_WORKERS**
   * **What it does:** Number of parallel processes used for hashing (default: up to 10 or CPU core count).
   * **Impact:**
      * More workers = faster runtime (up to your core limit)
      * Too many workers on low-memory systems may trigger swapping or slowdowns
      * More workers may result in missing cross-batch similarities
* **CHUNK\_COEF**:
   * **What it does:** Controls the number of files each worker gets (i.e. chunk size).
   * **Computed as:** `chunk_size = total_files // (MAX_WORKERS * CHUNK_COEF)`
   * **Impact:**
      * Lower value (e.g. 1–2) → larger batches → better global comparison but higher memory usage
      * Higher value (e.g. 4–10) → smaller batches → lower memory and faster per-batch processing, but may miss cross-batch similarities
* **MODE**: `image` or `video`.
   * Impact: (image) Computes a single hash per file (video) Extracts multiple frames per video and hashes them (slower, but much more accurate) 
* **FRAMES\_TO\_SAMPLE**:
   * **What it does:** Number of frames to extract and hash per video file
   * **Impact:**
      * Higher values (e.g. 60–90) = better coverage across time → better vibe detection, scene-level similarity
      * Lower values (e.g. 10–20) = faster, less precise
      * > For highly dynamic or longer videos, increase this to avoid missing variations
* **HASH\_SIZE**:
   * **What it does:** Size of the perceptual hash matrix (e.g. 8×8, 16×16, 32×32)
      * **Impact:**
         * Larger hash (e.g. 32) = more detail, higher grouping sensitivity, better for vibe sorting
         * Smaller hash (e.g. 8) = faster, but may miss nuanced similarity or group loosely
* **SIMILARITY\_THRESHOLD**:
   * **What it does:** Maximum allowed Hamming distance between hashes for files to be considered similar
   * Since hash size can vary, think of this as a **percentage of total hash bits**:
      * **Strict (0–2%)** → catches exact duplicates or near-identical encodes
      * **Moderate (3–7%)** → captures edited versions, recuts, color/brightness changes
      * **Loose (8–12%+)** → ideal for vibe grouping — same setting, outfit, or aesthetic
    * **Similarity % ≈ (SIMILARITY_THRESHOLD / HASH_SIZE²) × 100**
      * Example:
        - `HASH_SIZE = 32` → 32² = 1024 bits
        - `SIMILARITY_THRESHOLD = 75`
        - `75 / 1024 × 100 ≈ 7.3%`
      > Think of this as a vibe sensitivity dial — turn it up to group by feel, down to group by pixel-level sameness
---

## Installation

1. #### Create a Virtual Environment:
   `python3.11 -m venv venv`

3. #### Enter the Virtual Enviroment:
   `source venv/bin/activate   # Linux`

5. #### Install Dependencies:
   `pip install -r requirements.txt`

7. #### Make the launcher executable (Linux only):
   `chmod +x run.sh`

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

* #### View Help Message
  `./run.sh` or `./run.sh help`
* #### Run pHash on images using 4 workers and a stricter threshold
  `./run.sh phash image M_WORKERS=4 S_THRESH=8`
* #### Sample 30 frames for video dHash, no actual moves (dry run)
  `./run.sh dhash video S_FRAMES=30 D_RUN=true`
* #### Reset workspace
  `./run.sh reset`

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
