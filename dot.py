#!/usr/bin/env python3
"""Render images as Braille dot art with xterm-256 color and ncurses dim/normal/bold."""


import argparse
import curses
import sys
import os
import glob

import numpy as np
from PIL import Image, ImageFilter

BRAILLE_BASE = 0x2800
BRAILLE_MAP = (
    (0x01, 0x08),  # row 0
    (0x02, 0x10),  # row 1
    (0x04, 0x20),  # row 2
    (0x40, 0x80),  # row 3
)

# Dispersed-dot ordered dither matrix for the 4×2 braille grid.
BAYER_4x2 = np.array([
    [0, 4],
    [2, 6],
    [5, 1],
    [7, 3],
], dtype=np.float64)

# ── xterm-256 color cube helpers ──────────────────────────────────────────────
# Colors 16-231 form a 6×6×6 RGB cube. Values per axis: 0,95,135,175,215,255.
# Colors 232-255 are a 24-step greyscale ramp.
_CUBE_VALS = np.array([0, 0x5f, 0x87, 0xaf, 0xd7, 0xff], dtype=np.float64)
_GREY_VALS = np.array([8 + 10 * i for i in range(24)], dtype=np.float64)


def _build_xterm256_table():
    """Build an (N, 3) array of all xterm-256 RGB values (indices 16-255)."""
    table = np.zeros((240, 3), dtype=np.float64)
    # 6×6×6 cube: indices 0-215 → xterm 16-231
    idx = 0
    for r in _CUBE_VALS:
        for g in _CUBE_VALS:
            for b in _CUBE_VALS:
                table[idx] = (r, g, b)
                idx += 1
    # greyscale ramp: indices 216-239 → xterm 232-255
    for i, v in enumerate(_GREY_VALS):
        table[216 + i] = (v, v, v)
    return table


_XTERM_TABLE = _build_xterm256_table()  # (240, 3)


def _nearest_xterm256(r, g, b):
    """Return the xterm-256 color index (16-255) closest to an sRGB triplet (0-255)."""
    diff = _XTERM_TABLE - np.array([r, g, b], dtype=np.float64)
    dists = np.sum(diff * diff, axis=1)
    return int(np.argmin(dists)) + 16


def _init_color_pairs():
    """Initialise ncurses color pairs 1-240 mapping to xterm colors 16-255."""
    for i in range(240):
        xterm_idx = i + 16
        curses.init_pair(i + 1, xterm_idx, -1)  # fg=xterm color, bg=default


def _cell_to_global(local_brightness, attr, bounds):
    """Map a cell's local dot brightness back to global perceptual brightness."""
    if attr == curses.A_DIM:
        return local_brightness * bounds[0]
    elif attr == curses.A_NORMAL:
        return bounds[0] + local_brightness * (bounds[1] - bounds[0])
    else:
        return bounds[1] + local_brightness * (1.0 - bounds[1])


def srgb_to_linear(c):
    """Convert sRGB [0,1] to linear light."""
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    """Convert linear light to sRGB [0,1]."""
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(np.clip(c, 0, None), 1.0 / 2.4) - 0.055)




def _load_image(image_path, img_w, img_h, sharpen, color):
    """Load and prepare image data. Accepts a file path or PIL Image. Returns (frames, color_maps, oy, ox, fit_h, fit_w, durations)."""
    if isinstance(image_path, Image.Image):
        img = image_path
    else:
        img = Image.open(image_path)
    is_animated = getattr(img, "is_animated", False)
    n_frames = getattr(img, "n_frames", 1)
    frames = []
    color_maps = []
    durations = []
    for frame_idx in range(n_frames):
        if is_animated:
            img.seek(frame_idx)
            durations.append(img.info.get("duration", 100))
        if color:
            img_rgb = img.convert("RGB"); img_grey = img_rgb.convert("L")
        else:
            img_rgb = None; img_grey = img.convert("L")
        cell_cols, cell_rows = img_w // 2, img_h // 4
        img_aspect = img_grey.width / img_grey.height
        max_w, max_h = cell_cols * 2, cell_rows * 4
        fit_w, fit_h = (max_w, int(round(max_w / img_aspect))) if (max_w / img_aspect) <= max_h else (int(round(max_h * img_aspect)), max_h)
        fit_w, fit_h = min(fit_w, max_w), min(fit_h, max_h)
        img_grey_r = img_grey.resize((fit_w, fit_h), Image.LANCZOS)
        if sharpen: img_grey_r = img_grey_r.filter(ImageFilter.UnsharpMask(radius=1.2, percent=100, threshold=2))
        oy, ox = (img_h - fit_h) // 2, (img_w - fit_w) // 2
        raw = np.asarray(img_grey_r, dtype=np.float64)
        np.multiply(raw, 1.0/255.0, out=raw)  # in-place normalization
        linear = srgb_to_linear(raw)
        canvas = np.zeros((img_h, img_w), dtype=np.float64)
        canvas[oy:oy + fit_h, ox:ox + fit_w] = linear
        perceptual = linear_to_srgb(canvas)
        frames.append(perceptual)
        color_map = None
        if color and img_rgb is not None:
            img_rgb_r = img_rgb.resize((fit_w, fit_h), Image.LANCZOS)
            rgb_arr = np.asarray(img_rgb_r, dtype=np.float64)
            canvas_rgb = np.zeros((img_h, img_w, 3), dtype=np.float64)
            canvas_rgb[oy:oy + fit_h, ox:ox + fit_w] = rgb_arr
            blocks = canvas_rgb[:cell_rows*4, :cell_cols*2, :].reshape(cell_rows, 4, cell_cols, 2, 3)
            block_means = blocks.mean(axis=(1,3), dtype=np.float64)
            block_means_flat = block_means.reshape(-1, 3)
            diffs = block_means_flat[:, None, :] - _XTERM_TABLE[None, :, :]
            np.square(diffs, out=diffs)
            dists = np.sum(diffs, axis=2)
            color_indices = np.argmin(dists, axis=1) + 16
            color_map = color_indices.reshape(cell_rows, cell_cols).astype(np.int32)
        color_maps.append(color_map)
        if not is_animated: break
    return frames, color_maps, oy, ox, fit_h, fit_w, durations


# Helper to extract a video frame using ffmpeg and return a PIL Image
def extract_video_frame(path, frametime, extractformat):
    import subprocess, io
    vcodec = 'mjpeg' if extractformat == 'jpeg' else 'png'
    ffmpeg_cmd = [
        'ffmpeg', '-y', '-nostdin', '-hide_banner', '-loglevel', 'error',
        '-ss', str(frametime), '-i', path,
        '-an', '-threads', '1', '-vsync', '0',
        '-vframes', '1',
        '-f', 'image2pipe',
        '-vcodec', vcodec,
        '-']
    result = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0 or not result.stdout:
        raise RuntimeError(f"ffmpeg error: {result.stderr.decode()[:100]}")
    from PIL import Image
    img = Image.open(io.BytesIO(result.stdout))
    img.load()
    return img



def get_image_files(directory, include_videos=False):
    from pathlib import Path
    exts = ["png", "jpg", "jpeg", "bmp", "gif", "tiff", "webp"]
    if include_videos:
        exts += ["mp4", "mkv", "avi", "mov", "webm", "flv", "wmv", "mpeg", "mpg"]
    p = Path(directory)
    files = []
    for f in p.iterdir():
        if f.is_file():
            suffix = f.suffix.lower().lstrip('.')
            if suffix in exts:
                files.append(str(f.resolve()))
    files.sort()
    return files


def render(stdscr, image_files, idx, sharpen, dither_mode, color, single_image_mode=False, wait_time=5, slideshow=False):
    import time
    curses.curs_set(0)
    curses.use_default_colors()
    if color:
        curses.start_color()
        _init_color_pairs()

    n = len(image_files)
    def floyd_steinberg_dither(img):
        arr = img.copy()
        h, w = arr.shape
        for y in range(h):
            for x in range(w):
                old = arr[y, x]
                new = 1.0 if old > 0.5 else 0.0
                err = old - new
                arr[y, x] = new
                if x + 1 < w:
                    arr[y, x+1] += err * 7/16
                if y + 1 < h:
                    if x > 0:
                        arr[y+1, x-1] += err * 3/16
                    arr[y+1, x] += err * 5/16
                    if x + 1 < w:
                        arr[y+1, x+1] += err * 1/16
        return arr

    stdscr.clear()
    max_y, max_x = stdscr.getmaxyx()
    rows = max_y - 1
    cols = max_x - 1
    img_w = cols * 2
    img_h = rows * 4
    try:
        image_path = image_files[idx]
        # Determine display_name for the status bar
        display_name = None
        if isinstance(image_path, tuple) and len(image_path) == 2:
            image_path, display_name = image_path
        elif isinstance(image_path, Image.Image):
            display_name = '[video frame]'
        frames, color_maps, oy, ox, fit_h, fit_w, durations = _load_image(image_path, img_w, img_h, sharpen, color)
        is_animated = len(frames) > 1
        frame_idx = 0
        key = -1
        last_time = time.time()
        stdscr.nodelay(True)
    except Exception as e:
        stdscr.clear()
        stdscr.addstr(0, 0, f"Render error: {e}")
        stdscr.refresh()
        stdscr.getch()
        return -1
    while True:
        stdscr.clear()
        perceptual = frames[frame_idx]
        color_map = color_maps[frame_idx] if color_maps else None
        thresholds = (BAYER_4x2 + 0.5) / 8.0
        ATTR_BOUNDS = (0.30, 0.62)
        cell_rows = rows
        cell_cols = cols
        # Apply Floyd-Steinberg dithering if requested
        if dither_mode == "error":
            dithered = floyd_steinberg_dither(perceptual[:cell_rows*4, :cell_cols*2].copy())
            blocks = dithered.reshape(cell_rows, 4, cell_cols, 2)
        else:
            blocks = perceptual[:cell_rows*4, :cell_cols*2].reshape(cell_rows, 4, cell_cols, 2)
        block_means = blocks.mean(axis=(1,3))
        use_dither = dither_mode == "ordered"
        for cy in range(rows):
            for cx in range(cols):
                avg = block_means[cy, cx]
                if avg < ATTR_BOUNDS[0]:
                    attr = curses.A_DIM
                elif avg < ATTR_BOUNDS[1]:
                    attr = curses.A_NORMAL
                else:
                    attr = curses.A_BOLD
                code = BRAILLE_BASE
                block = blocks[cy, :, cx, :]
                for dr in range(4):
                    for dc in range(2):
                        t = thresholds[dr, dc] if use_dither else 0.5
                        if dither_mode == "error":
                            if block[dr, dc] > 0.5:
                                code |= BRAILLE_MAP[dr][dc]
                        else:
                            if block[dr, dc] > t:
                                code |= BRAILLE_MAP[dr][dc]
                if color and color_map is not None:
                    pair = color_map[cy, cx] - 16 + 1
                    attr |= curses.color_pair(pair)
                try:
                    stdscr.addstr(cy, cx, chr(code), attr)
                except curses.error:
                    pass
        # Show filename at the bottom
        try:
            if display_name:
                shown_name = os.path.basename(display_name)
            elif isinstance(image_path, (str, bytes, os.PathLike)):
                shown_name = os.path.basename(image_path)
            else:
                shown_name = '[video frame]'
            stdscr.addstr(rows, 0, f"[{idx+1}/{n}] {shown_name}", curses.A_REVERSE)
        except curses.error:
            pass
        stdscr.refresh()
        if is_animated:
            duration = durations[frame_idx] / 1000.0 if frame_idx < len(durations) else 0.1
            start_time = time.time()
            while True:
                key = stdscr.getch()
                if key != -1:
                    stdscr.nodelay(False)
                    return key
                if (time.time() - start_time) >= duration:
                    break
                time.sleep(0.01)
            frame_idx = (frame_idx + 1) % len(frames)
        else:
            # For non-animated images, just wait for key press once
            while True:
                key = stdscr.getch()
                if key != -1:
                    stdscr.nodelay(False)
                    return key
                time.sleep(0.01)
            break
    return key

def main():

    parser = argparse.ArgumentParser(description="Render an image or all images/videos in a directory as Braille dots using ncurses with optional xterm-256 color.")
    parser.add_argument("image", nargs="?", help="Path to the image file or directory (optional)")
    parser.add_argument("-S", "--no-sharpen", action="store_true", help="Disable edge sharpening")
    parser.add_argument("-C", "--no-color", action="store_true", help="Disable color (greyscale only with dim/normal/bold)")
    parser.add_argument("-d", "--dither", choices=["ordered", "error", "none"], default="ordered",
                        help="Dithering mode: ordered (default, clean), error (Floyd-Steinberg, smooth gradients), none")

    parser.add_argument("-w", "--wait", type=float, default=5, help="Wait time in seconds for single image mode or slideshow (default: 5)")
    parser.add_argument("-s", "--slideshow", action="store_true", help="Enable slideshow mode (auto-advance images, honors --wait)")
    parser.add_argument("-f", "--frametime", type=str, default="0:0:10", help="Time position (in format HH:MM:SS or seconds) to extract frame from video files (default: 0:0:10)")
    parser.add_argument("-x", "--extractformat", type=str, choices=["jpeg", "png"], default="jpeg", help="Format for extracted video frames: jpeg (default) or png")
    args = parser.parse_args()

    if args.image == '-':
        # Read image from stdin
        from PIL import Image
        import tempfile
        import shutil
        # Read stdin to a temporary file (since PIL.Image.open(sys.stdin.buffer) may not work for all formats)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
            shutil.copyfileobj(sys.stdin.buffer, tmp)
            tmp_path = tmp.name
        image_files = [tmp_path]
        idx = 0
        # Redirect stdin file descriptor to /dev/tty so curses reads input from the terminal
        # (removed local import os; using global import)
        try:
            tty_fd = os.open('/dev/tty', os.O_RDWR)
            orig_stdin_fd = os.dup(0)
            os.dup2(tty_fd, 0)
            os.close(tty_fd)
            try:
                curses.wrapper(lambda *a, **kw: render(*a, **kw, single_image_mode=True, wait_time=args.wait, slideshow=args.slideshow), image_files, idx, not args.no_sharpen, args.dither, not args.no_color)
            finally:
                os.dup2(orig_stdin_fd, 0)
                os.close(orig_stdin_fd)
        finally:
            os.unlink(tmp_path)
        return
    elif args.image:
        # If a directory is passed, render all images/videos in it
        if os.path.isdir(args.image):
            directory = os.path.abspath(args.image)
            image_files = get_image_files(directory, include_videos=args.frametime is not None)
            if not image_files:
                print(f"No images or videos found in directory: {directory}", file=sys.stderr)
                sys.exit(1)
            idx = 0
        else:
            # If --frametime is specified, treat as video and extract frame
            video_exts = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.mpeg', '.mpg']
            ext = os.path.splitext(args.image)[1].lower()
            if args.frametime and ext in video_exts:
                try:
                    img = extract_video_frame(args.image, args.frametime, args.extractformat)
                except Exception as e:
                    print(f"Failed to extract frame: {e}", file=sys.stderr)
                    sys.exit(1)
                image_files = [img]
                idx = 0
                curses.wrapper(lambda *a, **kw: render(*a, **kw, single_image_mode=True, wait_time=args.wait, slideshow=args.slideshow), image_files, idx, not args.no_sharpen, args.dither, not args.no_color)
                return
            abs_image = os.path.abspath(args.image)
            directory = os.path.dirname(abs_image) or os.getcwd()
            image_files = get_image_files(directory)
            if not image_files:
                print(f"No images found in directory: {directory}", file=sys.stderr)
                sys.exit(1)
            try:
                idx = image_files.index(abs_image)
            except ValueError:
                base = os.path.basename(abs_image)
                idx = next((i for i, f in enumerate(image_files) if os.path.basename(f) == base), 0)
    else:
        # No argument: use current directory
        directory = os.getcwd()
        include_videos = args.frametime is not None
        image_files = get_image_files(directory, include_videos=include_videos)
        if not image_files:
            print(f"No images or videos found in current directory.", file=sys.stderr)
            sys.exit(1)
        idx = 0


    # Always pass the video_exts and frametime to render for dynamic extraction
    video_exts = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.mpeg', '.mpg']

    def render_with_video_support(stdscr, image_files, start_idx, sharpen, dither_mode, color, single_image_mode=False, wait_time=5, slideshow=False):
        idx = start_idx
        n = len(image_files)
        while True:
            path = image_files[idx]
            ext = os.path.splitext(path)[1].lower()
            try:
                if ext in video_exts:
                    try:
                        img = extract_video_frame(path, args.frametime, args.extractformat)
                    except Exception as e:
                        stdscr.clear()
                        stdscr.addstr(0, 0, f"Video frame error: {e}")
                        stdscr.refresh()
                        stdscr.getch()
                        return
                    # Pass a tuple (image, filename) to render
                    key = render(stdscr, [(img, path)], 0, sharpen, dither_mode, color, single_image_mode=True, wait_time=wait_time, slideshow=False)
                else:
                    key = render(stdscr, image_files, idx, sharpen, dither_mode, color, single_image_mode=False, wait_time=wait_time, slideshow=False)
            except Exception as e:
                stdscr.clear()
                stdscr.addstr(0, 0, f"Error: {e}")
                stdscr.refresh()
                stdscr.getch()
                return
            # Navigation
            if key in (curses.KEY_RIGHT, ord('l'), ord(' ')):
                idx = (idx + 1) % n
            elif key in (curses.KEY_LEFT, ord('h')):
                idx = (idx - 1) % n
            elif key == curses.KEY_UP:
                idx = 0
            elif key == curses.KEY_DOWN:
                idx = n - 1
            elif key in (ord('q'), 27):
                break

    curses.wrapper(render_with_video_support, image_files, idx, not args.no_sharpen, args.dither, not args.no_color)


if __name__ == "__main__":
    main()
