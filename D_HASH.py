#!/usr/bin/env python3
# Soham Naik - 05/17/2025
import os
import shutil
import time
import argparse
import cv2
import numpy as np
from tqdm.contrib.concurrent import process_map
from scipy.spatial.distance import pdist, squareform
import av

# === PARSE ARGS ===
def parse_args():
    parser = argparse.ArgumentParser(
        description="Group visually similar media files using dHash (difference hash)."
    )
    parser.add_argument('--mode', choices=['image', 'video'], default='image',
                        help="Processing mode: 'image' or 'video'.")
    parser.add_argument('--input', dest='input_dir', default='input',
                        help="Source directory for files.")
    parser.add_argument('--output', dest='output_dir', default='output',
                        help="Destination directory for grouped results.")
    parser.add_argument('--workers', type=int, default=min(os.cpu_count(), 10),
                        help="Max parallel hashing processes (M_WORKERS).")
    parser.add_argument('--chunk-coef', type=int, default=4,
                        help="Batch coefficient (C_CHUNK).")
    parser.add_argument('--frames-to-sample', type=int, default=20,
                        help="Frames sampled per video (S_FRAMES).")
    parser.add_argument('--hash-size', type=int, default=8,
                        help="Hash grid size (S_HASH). 8 for dHash.")
    parser.add_argument('--threshold', dest='similarity_threshold', type=int, default=10,
                        help="Max Hamming distance for grouping (S_THRESH).")
    parser.add_argument('--dry-run', action='store_true',
                        help="Simulate file moves without executing (D_RUN).")
    return parser.parse_args()

# === UTILITIES ===
def restore_input_folder(output_dir, input_dir):
    if not os.path.exists(output_dir):
        return
    for root, _, files in os.walk(output_dir):
        for f in files:
            os.rename(os.path.join(root, f), os.path.join(input_dir, f))
    shutil.rmtree(output_dir)


def list_input_files(input_dir, mode):
    IMG_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
    VID_EXTS = ('.mp4', '.avi', '.mov', '.mkv', '.m4v')
    exts = VID_EXTS if mode == 'video' else IMG_EXTS
    return [f for f in sorted(os.listdir(input_dir))
            if os.path.isfile(os.path.join(input_dir, f)) and f.lower().endswith(exts)]


def compute_dhash(image_gray, hash_size):
    resized = cv2.resize(image_gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    return diff.ravel().astype(np.uint8)


def average_hash_from_stack(hash_stack, frame_count):
    return (np.sum(hash_stack, axis=0) > (frame_count // 2)).astype(np.uint8)


def hash_image(filename, input_dir, hash_size):
    path = os.path.join(input_dir, filename)
    img = cv2.imread(path)
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return filename, compute_dhash(gray, hash_size)


def get_frame_indices(total_frames, sample_count):
    return set(np.linspace(0, total_frames - 1, sample_count, dtype=int))


def hash_video(filename, input_dir, hash_size, frames_to_sample):
    path = os.path.join(input_dir, filename)
    try:
        container = av.open(path)
        stream = container.streams.video[0]
        total = stream.frames or sum(1 for _ in container.decode(stream))
        if stream.frames == 0:
            container.seek(0)
        indices = get_frame_indices(total, frames_to_sample)
        hashes = []
        for idx, frame in enumerate(container.decode(stream)):
            if idx in indices:
                gray_frame = frame.reformat(width=hash_size + 1,
                                            height=hash_size,
                                            format='gray8').to_ndarray()
                hashes.append(compute_dhash(gray_frame, hash_size))
                if len(hashes) >= frames_to_sample:
                    break
        container.close()
        if not hashes:
            return None
        return filename, average_hash_from_stack(np.stack(hashes), len(hashes))
    except Exception:
        return None


def hash_media(args_tuple):
    filename, input_dir, mode, hash_size, frames = args_tuple
    if mode == 'image':
        return hash_image(filename, input_dir, hash_size)
    return hash_video(filename, input_dir, hash_size, frames)


def group_similar_files(hash_list, threshold):
    names = [n for n, _ in hash_list]
    vecs = np.array([v for _, v in hash_list])
    dist_mat = squareform(pdist(vecs, metric='hamming')) * vecs.shape[1]
    groups, used = [], set()
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
            src, dst = os.path.join(input_dir, fname), os.path.join(dest, fname)
            if dry_run:
                print(f"DRY_RUN: would move {src} to {dst}")
            else:
                os.rename(src, dst)


def main():
    args = parse_args()
    print(f"Using {args.workers} workers for hashing")
    restore_input_folder(args.output_dir, args.input_dir)
    files = list_input_files(args.input_dir, args.mode)
    count = len(files)
    print(f"Found {count} {args.mode} files to process")

    chunk_size = max(1, count // (args.workers * args.chunk_coef))
    it_files = files
    it_dirs = [args.input_dir] * count
    it_modes = [args.mode] * count
    it_sizes = [args.hash_size] * count
    it_frames = [args.frames_to_sample] * count

    results = process_map(
        hash_media,
        zip(it_files, it_dirs, it_modes, it_sizes, it_frames),
        max_workers=args.workers,
        desc="Hashing files",
        chunksize=chunk_size
    )

    valid = [r for r in results if r]
    groups = group_similar_files(valid, args.similarity_threshold)
    save_groups(groups, args.input_dir, args.output_dir, args.dry_run)

    print(f"Identified {len(groups)} groups")

if __name__ == "__main__":
    start = time.time()
    main()
    print(f"Completed in {time.time() - start:.2f}s")
