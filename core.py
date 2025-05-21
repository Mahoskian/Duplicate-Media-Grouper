#!/usr/bin/env python3
# Soham Naik - 05/21/2025
import os
import shutil
import time
import argparse
import numpy as np
import cv2
import av
from tqdm.contrib.concurrent import process_map
from scipy.spatial.distance import pdist, squareform

# Import hashing functions
from hasher import dhash_compute, phash_compute, whash_compute

# Module-level compute function for worker
_compute_fn = None

def parse_args():
    parser = argparse.ArgumentParser(
        description="Group visually similar media using dHash, pHash, or wHash."
    )
    parser.add_argument(
        '--hash-type', choices=['dhash','phash','whash'], required=True,
        help="Select hashing algorithm."
    )
    parser.add_argument(
        '--mode', choices=['image','video'], default='image',
        help="Processing mode: image or video."
    )
    parser.add_argument(
        '--input', dest='input_dir', default='input',
        help="Directory containing media files."
    )
    parser.add_argument(
        '--output', dest='output_dir', default='output',
        help="Directory for grouped output."
    )
    parser.add_argument(
        '--workers', type=int, default=min(os.cpu_count(), 10),
        help="Max parallel hashing processes."
    )
    parser.add_argument(
        '--chunk-coef', type=int, default=4,
        help="Batch coefficient for chunksize calculation."
    )
    parser.add_argument(
        '--frames-to-sample', type=int, default=20,
        help="Number of frames to sample per video."
    )
    parser.add_argument(
        '--hash-size', type=int, default=None,
        help="Hash grid size override (uses algorithm default if omitted)."
    )
    parser.add_argument(
        '--threshold', dest='similarity_threshold', type=int, default=None,
        help="Similarity threshold override (uses algorithm default if omitted)."
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help="Simulate file moves without executing."
    )
    parser.add_argument(
        '--graph', action='store_true',
        help="Plot clusters in 2D after grouping."
    )
    return parser.parse_args()


def restore_input_folder(output_dir, input_dir):
    if not os.path.exists(output_dir):
        return
    for root, _, files in os.walk(output_dir):
        for f in files:
            os.rename(os.path.join(root, f), os.path.join(input_dir, f))
    shutil.rmtree(output_dir)


def list_input_files(input_dir, mode):
    IMG_EXTS = ('.jpg','.jpeg','.png','.bmp','.tiff','.webp')
    VID_EXTS = ('.mp4','.avi','.mov','.mkv','.m4v')
    exts = VID_EXTS if mode == 'video' else IMG_EXTS
    return [
        f for f in sorted(os.listdir(input_dir))
        if os.path.isfile(os.path.join(input_dir, f)) and f.lower().endswith(exts)
    ]


def average_hash_from_stack(hash_stack, frame_count):
    return (np.sum(hash_stack, axis=0) > (frame_count // 2)).astype(np.uint8)


def get_frame_indices(total_frames, sample_count):
    return set(np.linspace(0, total_frames - 1, sample_count, dtype=int))


def hash_image(filename, input_dir, hash_size):
    path = os.path.join(input_dir, filename)
    img = cv2.imread(path)
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return filename, _compute_fn(gray, hash_size)


def hash_video(filename, input_dir, hash_size, frames_to_sample):
    path = os.path.join(input_dir, filename)
    try:
        container = av.open(path)
        stream = container.streams.video[0]
        total = stream.frames or sum(1 for _ in container.decode(stream))
        indices = get_frame_indices(total, frames_to_sample)
        hashes = []
        for idx, frame in enumerate(container.decode(stream)):
            if idx in indices:
                arr = frame.to_ndarray(format='bgr24')
                gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
                hashes.append(_compute_fn(gray, hash_size))
                if len(hashes) >= frames_to_sample:
                    break
        container.close()
        if not hashes:
            return None
        return filename, average_hash_from_stack(np.stack(hashes), len(hashes))
    except Exception:
        return None


def cluster_hashes(hash_list, threshold):
    names = [n for n, _ in hash_list]
    vecs = np.array([v for _, v in hash_list])
    dist_mat = squareform(pdist(vecs, metric='hamming')) * vecs.shape[1]
    groups = []
    used = set()
    for i, name in enumerate(names):
        if i in used:
            continue
        grp = [name]
        used.add(i)
        for j in range(i + 1, len(names)):
            if j not in used and dist_mat[i, j] <= threshold:
                grp.append(names[j])
                used.add(j)
        if len(grp) > 1:
            groups.append(grp)
    return groups


def save_groups(groups, input_dir, output_dir, dry_run):
    os.makedirs(output_dir, exist_ok=True)
    for idx, grp in enumerate(groups, start=1):
        dest = os.path.join(output_dir, f"group_{idx}")
        os.makedirs(dest, exist_ok=True)
        for fname in grp:
            src = os.path.join(input_dir, fname)
            dst = os.path.join(dest, fname)
            if dry_run:
                print(f"DRY_RUN: {src} -> {dst}")
            else:
                os.rename(src, dst)


def worker(task):
    # Top-level worker for multiprocessing pickling.
    name, inp, mode, sz, fr = task
    if mode == 'image':
        return hash_image(name, inp, sz)
    return hash_video(name, inp, sz, fr)


def main():
    global _compute_fn
    args = parse_args()

    # Choose algorithm and defaults
    if args.hash_type == 'dhash':
        _compute_fn = dhash_compute
        default_size, default_thresh = 8, 10
    elif args.hash_type == 'phash':
        _compute_fn = phash_compute
        default_size, default_thresh = 16, 25
    else:
        _compute_fn = whash_compute
        default_size, default_thresh = 8, 10

    # Apply overrides or defaults
    hash_size = args.hash_size or default_size
    thresh = args.similarity_threshold or default_thresh

    start_time = time.time()
    print(f"Using {args.workers} workers, hash={args.hash_type}, size={hash_size}, thresh={thresh}")

    # Prepare workspace
    restore_input_folder(args.output_dir, args.input_dir)
    files = list_input_files(args.input_dir, args.mode)
    print(f"Found {len(files)} {args.mode} files to process")

    # Chunking for multiprocessing
    chunk_size = max(1, len(files) // (args.workers * args.chunk_coef))
    tasks = zip(
        files,
        [args.input_dir] * len(files),
        [args.mode] * len(files),
        [hash_size] * len(files),
        [args.frames_to_sample] * len(files)
    )

    results = process_map(
        worker,
        tasks,
        max_workers=args.workers,
        desc="Hashing files",
        chunksize=chunk_size
    )

    valid = [r for r in results if r]
    groups = cluster_hashes(valid, thresh)

    # Graphing here

    save_groups(groups, args.input_dir, args.output_dir, args.dry_run)

    print(f"Identified {len(groups)} groups")
    print(f"Completed in {time.time() - start_time:.2f}s")


if __name__ == '__main__':
    main()
