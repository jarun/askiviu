#!/usr/bin/env python3
"""Render images as Braille art with xterm-256 color and ncurses dim/normal/bold."""


import argparse
from concurrent.futures import ThreadPoolExecutor
import curses
import sys
import os

import numpy as np
from PIL import Image, ImageFilter

_VERSION_ = "0.1"
_AUTHOR_ = "Arun Prakash Jana"
_AUTHOR_EMAIL_ = "engineerarun@gmail.com"
_LICENSE_ = "MIT"
_WEBPAGE_ = "https://github.com/jarun/dotz"

BRAILLE_BASE = 0x2800
BRAILLE_MAP = (
    (0x01, 0x08),  # row 0
    (0x02, 0x10),  # row 1
    (0x04, 0x20),  # row 2
    (0x40, 0x80),  # row 3
)
VIDEO_EXTS = frozenset({".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".mpeg", ".mpg"})
IMAGE_EXTS = frozenset({"png", "jpg", "jpeg", "bmp", "gif", "tiff", "webp"})
VIDEO_EXTS_NO_DOT = frozenset(ext.lstrip(".") for ext in VIDEO_EXTS)

# Ordered dither matrix for the 4×2 braille grid.
BAYER_4x2 = np.array([
    [0, 4],
    [2, 6],
    [5, 1],
    [7, 3],
], dtype=np.float64)
ORDERED_THRESHOLDS = (BAYER_4x2 + 0.5) / 8.0

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


def _init_color_pairs():
    """Initialise ncurses color pairs 1-240 mapping to xterm colors 16-255."""
    for i in range(240):
        xterm_idx = i + 16
        curses.init_pair(i + 1, xterm_idx, -1)  # fg=xterm color, bg=default


def srgb_to_linear(c):
    """Convert sRGB [0,1] to linear light."""
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    """Convert linear light to sRGB [0,1]."""
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(np.clip(c, 0, None), 1.0 / 2.4) - 0.055)


def _load_image(image_path, img_w, img_h, sharpen, color):
    """Load and prepare image data. Accepts a file path or PIL Image. Returns (frames, color_maps, oy, ox, fit_h, fit_w, durations)."""
    img = image_path if isinstance(image_path, Image.Image) else Image.open(image_path)
    is_animated = getattr(img, "is_animated", False)
    n_frames = getattr(img, "n_frames", 1)
    cell_cols, cell_rows = img_w // 2, img_h // 4
    max_w, max_h = cell_cols * 2, cell_rows * 4
    frames = []
    color_maps = []
    durations = []
    for frame_idx in range(n_frames):
        if is_animated:
            img.seek(frame_idx)
            durations.append(img.info.get("duration", 100))
        img_rgb = img.convert("RGB") if color else None
        img_grey = img_rgb.convert("L") if color else img.convert("L")
        img_aspect = img_grey.width / img_grey.height
        fit_w, fit_h = (max_w, int(round(max_w / img_aspect))) if (max_w / img_aspect) <= max_h else (int(round(max_h * img_aspect)), max_h)
        fit_w, fit_h = min(fit_w, max_w), min(fit_h, max_h)
        img_grey_r = img_grey.resize((fit_w, fit_h), Image.LANCZOS)
        if sharpen: img_grey_r = img_grey_r.filter(ImageFilter.UnsharpMask(radius=1.2, percent=100, threshold=2))
        oy, ox = (img_h - fit_h) // 2, (img_w - fit_w) // 2
        raw = np.asarray(img_grey_r, dtype=np.float64) / 255.0
        linear = srgb_to_linear(raw)
        canvas = np.zeros((img_h, img_w), dtype=np.float64)
        canvas[oy:oy + fit_h, ox:ox + fit_w] = linear
        perceptual = linear_to_srgb(canvas)
        frames.append(perceptual)
        if color and img_rgb is not None:
            img_rgb_r = img_rgb.resize((fit_w, fit_h), Image.LANCZOS)
            rgb_arr = np.asarray(img_rgb_r, dtype=np.float64)
            canvas_rgb = np.zeros((img_h, img_w, 3), dtype=np.float64)
            canvas_rgb[oy:oy + fit_h, ox:ox + fit_w] = rgb_arr
            blocks = canvas_rgb[:cell_rows*4, :cell_cols*2, :].reshape(cell_rows, 4, cell_cols, 2, 3)
            block_means = blocks.mean(axis=(1, 3), dtype=np.float64)
            block_means_flat = block_means.reshape(-1, 3)
            diffs = block_means_flat[:, None, :] - _XTERM_TABLE[None, :, :]
            np.square(diffs, out=diffs)
            dists = np.sum(diffs, axis=2)
            color_indices = np.argmin(dists, axis=1) + 16
            color_map = color_indices.reshape(cell_rows, cell_cols).astype(np.int32)
        else:
            color_map = None
        color_maps.append(color_map)
        if not is_animated: break
    return frames, color_maps, oy, ox, fit_h, fit_w, durations


# Helper to extract a video frame using ffmpeg and return a PIL Image
def _is_video_path(path):
    return os.path.splitext(str(path))[1].lower() in VIDEO_EXTS


def extract_video_frame(path, frametime, extractformat):
    import subprocess, io
    vcodec = 'mjpeg' if extractformat == 'jpeg' else 'png'
    ffmpeg_cmd = [
        'ffmpeg', '-y', '-nostdin', '-hide_banner', '-loglevel', 'error',
        '-skip_frame', 'nokey', '-ss', str(int(frametime)), '-i', path,
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
    exts = IMAGE_EXTS | VIDEO_EXTS_NO_DOT if include_videos else IMAGE_EXTS
    files = []
    with os.scandir(directory) as entries:
        for entry in entries:
            if not entry.is_file():
                continue
            _, ext = os.path.splitext(entry.name)
            if ext.lower().lstrip(".") in exts:
                files.append(os.path.realpath(entry.path))
    files.sort()
    return files


def _display_name(image_path, display_name):
    return os.path.basename(display_name or image_path or "[video frame]") if display_name or isinstance(image_path, (str, bytes, os.PathLike)) else "[video frame]"


def _prepare_render_item(image_item, img_w, img_h, sharpen, color, seek, extractformat):
    """Prepare renderable frame buffers for one item. Safe to run in worker threads."""
    image_path = image_item
    display_name = None
    if _is_video_path(image_path):
        img = extract_video_frame(image_path, seek, extractformat)
        display_name = image_path
        frames, color_maps, oy, ox, fit_h, fit_w, durations = _load_image(img, img_w, img_h, sharpen, color)
    else:
        if isinstance(image_path, tuple) and len(image_path) == 2:
            image_path, display_name = image_path
        elif isinstance(image_path, Image.Image):
            display_name = '[video frame]'
        frames, color_maps, oy, ox, fit_h, fit_w, durations = _load_image(image_path, img_w, img_h, sharpen, color)
    return {
        "frames": frames,
        "color_maps": color_maps,
        "durations": durations,
        "shown_name": _display_name(image_path, display_name),
    }


def _clamp_delay(delay):
    try:
        delay = int(delay)
    except (TypeError, ValueError):
        return 1
    return max(1, min(60, delay))


def _format_status(idx, total, shown_name, zoom_factor, slideshow_active, slideshow_reverse, delay):
    slideshow_mode = "reverse" if slideshow_reverse else "forward"
    slideshow_status = slideshow_mode if slideshow_active else "off"
    return f"[{idx + 1}/{total}] {shown_name} | {zoom_factor:.2f}x | slideshow: {slideshow_status} | {delay}s"


def _update_pan_offset(pan_y, pan_x, key):
    pan_step = 0.125
    if key == 'pan_left':
        pan_x -= pan_step
    elif key == 'pan_right':
        pan_x += pan_step
    elif key == 'pan_up':
        pan_y -= pan_step
    elif key == 'pan_down':
        pan_y += pan_step
    return max(-1.0, min(1.0, pan_y)), max(-1.0, min(1.0, pan_x))


def _zoom_array(array, zoom_factor, target_size, pan_offset=(0.0, 0.0), fill_value=0):
    """Return a centered, optionally panned nearest-neighbor zoom of a two-dimensional array."""
    if array is None:
        return None

    target_h, target_w = target_size
    zoom_factor = float(zoom_factor or 1.0)
    pan_y, pan_x = pan_offset
    pan_y = max(-1.0, min(1.0, float(pan_y)))
    pan_x = max(-1.0, min(1.0, float(pan_x)))
    if zoom_factor <= 0:
        zoom_factor = 1.0
    if zoom_factor == 1.0 and array.shape == (target_h, target_w):
        return array

    source_h, source_w = array.shape
    if zoom_factor > 1.0:
        visible_h = source_h / zoom_factor
        visible_w = source_w / zoom_factor
        top = (source_h - visible_h) * (pan_y + 1.0) / 2.0
        left = (source_w - visible_w) * (pan_x + 1.0) / 2.0
        row_indices = np.minimum(
            source_h - 1,
            (top + (np.arange(target_h) + 0.5) * visible_h / target_h).astype(np.intp),
        )
        col_indices = np.minimum(
            source_w - 1,
            (left + (np.arange(target_w) + 0.5) * visible_w / target_w).astype(np.intp),
        )
        return array[row_indices[:, None], col_indices]

    scaled_h = max(1, int(round(target_h * zoom_factor)))
    scaled_w = max(1, int(round(target_w * zoom_factor)))
    row_indices = np.minimum(
        source_h - 1,
        ((np.arange(scaled_h) + 0.5) * source_h / scaled_h).astype(np.intp),
    )
    col_indices = np.minimum(
        source_w - 1,
        ((np.arange(scaled_w) + 0.5) * source_w / scaled_w).astype(np.intp),
    )
    result = np.full((target_h, target_w), fill_value, dtype=array.dtype)
    top = (target_h - scaled_h) // 2
    left = (target_w - scaled_w) // 2
    result[top:top + scaled_h, left:left + scaled_w] = array[row_indices[:, None], col_indices]
    return result


def _update_slideshow_state(slideshow_active, slideshow_reverse, key):
    if key == 'toggle_slideshow':
        if slideshow_active and slideshow_reverse:
            return True, False
        if slideshow_active:
            return False, False
        return True, False
    if key == 'toggle_slideshow_reverse':
        if slideshow_active and slideshow_reverse:
            return False, False
        return True, True
    return slideshow_active, slideshow_reverse


def _draw_braille_rows(stdscr, rows, cols, blocks, block_means, thresholds, color_map, color, use_error_dither, use_ordered_dither):
    ATTR_BOUNDS = (0.30, 0.62)
    half_threshold = 0.5
    color_pair = curses.color_pair
    for cy in range(rows):
        segments = []
        current_attr = None
        current_chars = []
        start_x = 0
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
            if use_error_dither:
                for dr in range(4):
                    for dc in range(2):
                        if block[dr, dc] > half_threshold:
                            code |= BRAILLE_MAP[dr][dc]
            elif use_ordered_dither:
                for dr in range(4):
                    for dc in range(2):
                        if block[dr, dc] > thresholds[dr, dc]:
                            code |= BRAILLE_MAP[dr][dc]
            else:
                for dr in range(4):
                    for dc in range(2):
                        if block[dr, dc] > half_threshold:
                            code |= BRAILLE_MAP[dr][dc]
            if color and color_map is not None and color_map[cy, cx] >= 16:
                attr |= color_pair(color_map[cy, cx] - 16 + 1)
            ch = chr(code)
            if current_attr is None or current_attr != attr:
                if current_chars:
                    segments.append((start_x, current_attr, "".join(current_chars)))
                start_x = cx
                current_attr = attr
                current_chars = [ch]
            else:
                current_chars.append(ch)
        if current_chars:
            segments.append((start_x, current_attr, "".join(current_chars)))
        for x, attr, text in segments:
            try:
                stdscr.addstr(cy, x, text, attr)
            except curses.error:
                pass


def render(stdscr, image_files, idx, sharpen, dither_mode, color, single_image_mode=False, wait_time=5, slideshow=False, slideshow_reverse=False, prepared=None, zoom_factor=1.0, pan_offset=(0.0, 0.0)):
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

    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()
    rows = max_y
    cols = max_x
    status_y = max_y - 1
    img_w = cols * 2
    img_h = rows * 4
    try:
        image_item = image_files[idx]
        if prepared is None:
            seek = getattr(render, '_seek', 10)
            fmt = getattr(render, '_format', 'jpeg')
            prepared = _prepare_render_item(image_item, img_w, img_h, sharpen, color, seek, fmt)
        frames = prepared["frames"]
        color_maps = prepared["color_maps"]
        durations = prepared["durations"]
        shown_name = prepared["shown_name"]
        is_animated = len(frames) > 1
        frame_idx = 0
        key = -1
        stdscr.nodelay(True)
    except Exception as e:
        stdscr.clear()
        stdscr.addstr(0, 0, f"Render error: {e}")
        stdscr.refresh()
        stdscr.getch()
        return -1
    thresholds = ORDERED_THRESHOLDS
    use_error_dither = dither_mode == "error"
    use_ordered_dither = dither_mode == "ordered"
    while True:
        stdscr.erase()
        perceptual = frames[frame_idx]
        color_map = color_maps[frame_idx] if color_maps else None
        frame_view = perceptual[:rows * 4, :cols * 2]
        frame_view = _zoom_array(frame_view, zoom_factor, target_size=(rows * 4, cols * 2), pan_offset=pan_offset)
        color_map = _zoom_array(color_map, zoom_factor, target_size=(rows, cols), pan_offset=pan_offset)
        if use_error_dither:
            dithered = floyd_steinberg_dither(frame_view.copy())
            blocks = dithered.reshape(rows, 4, cols, 2)
        else:
            blocks = frame_view.reshape(rows, 4, cols, 2)
        block_means = blocks.mean(axis=(1, 3))
        _draw_braille_rows(stdscr, rows, cols, blocks, block_means, thresholds, color_map, color, use_error_dither, use_ordered_dither)
        try:
            status = _format_status(idx, n, shown_name, zoom_factor, slideshow, slideshow_reverse, wait_time)
            stdscr.addnstr(status_y, 0, status, max_x - 1, curses.A_REVERSE)
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
                    if key == ord('+'):
                        return 'zoom_in'
                    if key == ord('-'):
                        return 'zoom_out'
                    if key == ord('0'):
                        return 'reset_zoom'
                    if key == ord('h'):
                        return 'pan_left'
                    if key == ord('j'):
                        return 'pan_down'
                    if key == ord('k'):
                        return 'pan_up'
                    if key == ord('l'):
                        return 'pan_right'
                    return key
                if (time.time() - start_time) >= duration:
                    break
                time.sleep(0.01)
            frame_idx = (frame_idx + 1) % len(frames)
        else:
            start_time = time.time() if slideshow else None
            while True:
                key = stdscr.getch()
                if key == ord('s'):
                    return 'toggle_slideshow'
                if key == ord('S'):
                    return 'toggle_slideshow_reverse'
                if key == ord('D'):
                    return 'increase_delay'
                if key == ord('d'):
                    return 'decrease_delay'
                if key == ord('+'):
                    return 'zoom_in'
                if key == ord('-'):
                    return 'zoom_out'
                if key == ord('0'):
                    return 'reset_zoom'
                if key == ord('h'):
                    return 'pan_left'
                if key == ord('j'):
                    return 'pan_down'
                if key == ord('k'):
                    return 'pan_up'
                if key == ord('l'):
                    return 'pan_right'
                if key != -1:
                    stdscr.nodelay(False)
                    return key
                if slideshow and start_time is not None and (time.time() - start_time) >= wait_time:
                    return 'slideshow_next'
                time.sleep(0.01)
    return key


def main():
    class ExtendedArgumentParser(argparse.ArgumentParser):
        @staticmethod
        def print_extended_help(file=None):
            if file is None:
                file = sys.stderr
            file.write(
                "\n"
                f"Version: {_VERSION_}\n"
                f"Author: {_AUTHOR_} <{_AUTHOR_EMAIL_}>\n"
                f"License: {_LICENSE_}\n"
                f"Webpage: {_WEBPAGE_}\n"
            )

        def print_help(self, file=None):
            super().print_help(file)
            self.print_extended_help(file)

    parser = ExtendedArgumentParser(description="Render an image or all images/videos in a directory as Braille cells using ncurses with optional xterm-256 color.")
    parser.add_argument("path", nargs="?", help="Path to the image/video file or directory (optional)")
    parser.add_argument("-S", "--no-sharpen", action="store_true", help="Disable edge sharpening")
    parser.add_argument("-C", "--no-color", action="store_true", help="Disable color (greyscale only with dim/normal/bold)")
    parser.add_argument("-d", "--dither", choices=["ordered", "error", "none"], default="ordered",
                        help="Dithering mode: ordered (default, clean), error (Floyd-Steinberg, smooth gradients), none")

    parser.add_argument("-s", "--slideshow", dest="delay", nargs="?", const=5, type=int, help="Enable slideshow mode with optional integer delay in seconds (default: 5).")
    parser.add_argument("-k", "--seek", type=int, default=10, help="Seek position to extract frame from videos in seconds (default: 10)")
    parser.add_argument("-f", "--format", type=str, choices=["jpeg", "png"], default="jpeg", help="Format for extracted video frames: jpeg (default) or png")
    parser.add_argument("-v", "--version", action="version", version=_VERSION_)
    args = parser.parse_args()

    slideshow = args.delay is not None
    slideshow_delay = _clamp_delay(args.delay if slideshow else 5)

    if args.path == '-':
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
                curses.wrapper(lambda *a, **kw: render(*a, **kw, single_image_mode=True, wait_time=slideshow_delay, slideshow=slideshow), image_files, idx, not args.no_sharpen, args.dither, not args.no_color)
            finally:
                os.dup2(orig_stdin_fd, 0)
                os.close(orig_stdin_fd)
        finally:
            os.unlink(tmp_path)
        return
    elif args.path:
        # If a directory is passed, render all images/videos in it
        if os.path.isdir(args.path):
            directory = os.path.abspath(args.path)
            image_files = get_image_files(directory, include_videos=args.seek is not None)
            if not image_files:
                print(f"No images or videos found in directory: {directory}", file=sys.stderr)
                sys.exit(1)
            idx = 0
        else:
            abs_path = os.path.abspath(args.path)
            directory = os.path.dirname(abs_path) or os.getcwd()
            # Always include videos if the selected file is a video
            include_videos = _is_video_path(abs_path) or args.seek is not None
            image_files = get_image_files(directory, include_videos=include_videos)
            if not image_files:
                print(f"No images or videos found in directory: {directory}", file=sys.stderr)
                sys.exit(1)
            try:
                idx = image_files.index(abs_path)
            except ValueError:
                base = os.path.basename(abs_path)
                idx = next((i for i, f in enumerate(image_files) if os.path.basename(f) == base), 0)
    else:
        # No argument: use current directory
        directory = os.getcwd()
        include_videos = args.seek is not None
        image_files = get_image_files(directory, include_videos=include_videos)
        if not image_files:
            print(f"No images or videos found in current directory.", file=sys.stderr)
            sys.exit(1)
        idx = 0


    # Pass seek and format to render via function attributes for video frame extraction
    def render_with_video_support(stdscr, image_files, start_idx, sharpen, dither_mode, color, single_image_mode=False, wait_time=5, slideshow=False):
        idx = start_idx
        n = len(image_files)
        max_workers = min(4, max(2, os.cpu_count() or 2))
        preload_futures = {}

        def viewport_dims():
            max_y, max_x = stdscr.getmaxyx()
            return max_x * 2, max_y * 4

        def preload_key(image_idx, img_w, img_h):
            return (image_idx, img_w, img_h, sharpen, color, args.seek, args.format)

        def schedule_preload(image_idx, img_w, img_h, executor):
            key = preload_key(image_idx, img_w, img_h)
            if key in preload_futures:
                return
            preload_futures[key] = executor.submit(
                _prepare_render_item,
                image_files[image_idx],
                img_w,
                img_h,
                sharpen,
                color,
                args.seek,
                args.format,
            )

        def get_preloaded(image_idx, img_w, img_h):
            key = preload_key(image_idx, img_w, img_h)
            future = preload_futures.get(key)
            if future is None:
                return None
            try:
                return future.result()
            finally:
                preload_futures.pop(key, None)

        def trim_preload_cache(keep_indices, img_w, img_h):
            keep_keys = {preload_key(i, img_w, img_h) for i in keep_indices}
            stale_keys = [k for k in preload_futures.keys() if k not in keep_keys]
            for key in stale_keys:
                future = preload_futures.pop(key)
                future.cancel()

        # Pass seek/format to render via function attributes
        render._seek = args.seek
        render._format = args.format
        slideshow_active = slideshow
        slideshow_reverse = False
        current_delay = wait_time
        zoom_factor = 1.0
        pan_y = 0.0
        pan_x = 0.0
        last_rendered_idx = idx
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            while True:
                if idx != last_rendered_idx:
                    stdscr.erase()
                    zoom_factor = 1.0
                    pan_y = 0.0
                    pan_x = 0.0
                    last_rendered_idx = idx

                img_w, img_h = viewport_dims()
                next_idx = (idx + 1) % n
                prev_idx = (idx - 1) % n
                schedule_preload(idx, img_w, img_h, executor)
                schedule_preload(next_idx, img_w, img_h, executor)
                schedule_preload(prev_idx, img_w, img_h, executor)
                trim_preload_cache({idx, next_idx, prev_idx}, img_w, img_h)

                try:
                    prepared = get_preloaded(idx, img_w, img_h)
                    key = render(
                        stdscr,
                        image_files,
                        idx,
                        sharpen,
                        dither_mode,
                        color,
                        single_image_mode=False,
                        wait_time=current_delay,
                        slideshow=slideshow_active,
                        slideshow_reverse=slideshow_reverse,
                        prepared=prepared,
                        zoom_factor=zoom_factor,
                        pan_offset=(pan_y, pan_x),
                    )
                except Exception as e:
                    stdscr.clear()
                    stdscr.addstr(0, 0, f"Error: {e}")
                    stdscr.refresh()
                    stdscr.getch()
                    return
                # Navigation
                if key == 'zoom_in':
                    zoom_factor = min(4.0, zoom_factor + 0.25)
                    continue
                if key == 'zoom_out':
                    zoom_factor = max(0.25, zoom_factor - 0.25)
                    if zoom_factor <= 1.0:
                        pan_y = 0.0
                        pan_x = 0.0
                    continue
                if key == 'reset_zoom':
                    zoom_factor = 1.0
                    pan_y = 0.0
                    pan_x = 0.0
                    continue
                if key in ('pan_left', 'pan_right', 'pan_up', 'pan_down'):
                    if zoom_factor > 1.0:
                        pan_y, pan_x = _update_pan_offset(pan_y, pan_x, key)
                    continue
                if key == 'increase_delay':
                    current_delay = _clamp_delay(current_delay + 1)
                    continue
                if key == 'decrease_delay':
                    current_delay = _clamp_delay(current_delay - 1)
                    continue
                slideshow_active, slideshow_reverse = _update_slideshow_state(slideshow_active, slideshow_reverse, key)
                if key in ('toggle_slideshow', 'toggle_slideshow_reverse'):
                    continue
                if slideshow_active and key not in ('slideshow_next', -1, 'toggle_slideshow', 'toggle_slideshow_reverse'):
                    # Any other key disables slideshow
                    slideshow_active = False
                    slideshow_reverse = False
                if key == 'slideshow_next':
                    if slideshow_reverse:
                        idx = (idx - 1) % n
                    else:
                        idx = (idx + 1) % n
                elif key in (curses.KEY_RIGHT, ord('n'), ord(' ')):
                    idx = (idx + 1) % n
                elif key in (curses.KEY_LEFT, ord('p')):
                    idx = (idx - 1) % n
                elif key == curses.KEY_UP:
                    idx = 0
                elif key == curses.KEY_DOWN:
                    idx = n - 1
                elif key in (ord('q'), 27):
                    break

    curses.wrapper(render_with_video_support, image_files, idx, not args.no_sharpen, args.dither, not args.no_color, wait_time=slideshow_delay, slideshow=slideshow)


if __name__ == "__main__":
    main()
