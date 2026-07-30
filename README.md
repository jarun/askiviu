# dotz

Render images and video previews as Braille art in the terminal with xterm-256 color and ncurses dim/normal/bold attributes.

It was written to be used as a terminal image viewer with [`nnn`](https://github.com/jarun/nnn). Works independently too.

## Features

- Braille art rendering for images
- Animated GIF support
- xterm-256 color and grayscale
- Dithering options (ordered, error diffusion)
- Video preview (frame extraction with ffmpeg)
- File metadata panel
- Zoom in, zoom out, pan while zoom
- Rotate clockwise, flip
- Bounded background preloading
- Keyboard navigation and slideshow mode
- Video playback with seek controls

<br>
<img width="1323" height="826" alt="image_01" src="https://github.com/user-attachments/assets/f2becbbc-cfeb-42b3-bd92-3882ff3fb570" />
<br><br>
<img width="1333" height="827" alt="image_02" src="https://github.com/user-attachments/assets/62bc16a8-246b-4b5a-a11e-fd0faa5c8066" />
<br><br>
<img width="1301" height="954" alt="image_03" src="https://github.com/user-attachments/assets/609805be-c0c5-4815-bb33-3bc70d69c152" />


## Installation

Install from PyPI:

```sh
pip install dotz
```

Or install from the source repository:

```sh
# Install system dependencies (e.g., ffmpeg)
sudo apt-get install ffmpeg  # or use your OS package manager

# Install Python dependencies and the CLI tool
sudo pip3 install .
```

After installation, you can run the tool using:

```sh
dotz [options] <file-or-directory>
```

## Usage

Run the local workspace copy directly with:

```sh
python3 dotz.py [options] <file-or-directory>
```

Or use the installed entry point after reinstalling from the repository:

```
usage: dotz [-h] [-S] [-C] [-d {ordered,error,none}] [-s [DELAY]] [-k SEEK] [-f {jpeg,png}] [path]

Render an image or all images/videos in a directory as Braille cells using ncurses with optional xterm-256 color.

positional arguments:
  path                  Path to the image/video file or directory (optional)

options:
  -h, --help            show this help message and exit
  -S, --no-sharpen      Disable edge sharpening
  -C, --no-color        Disable color (greyscale only with dim/normal/bold)
  -d {ordered,error,none}, --dither {ordered,error,none}
                        Dithering mode: ordered (default, clean), error (Floyd-Steinberg, smooth gradients), none
  -s [DELAY], --slideshow [DELAY]
                        Enable slideshow mode with optional integer delay in seconds (default: 5).
  -k SEEK, --seek SEEK  Seek position to extract frame from videos in seconds (default: 10)
  -f {jpeg,png}, --format {jpeg,png}
                        Format for extracted video frames: jpeg (default) or png
```

Dotz keeps the current item plus one next and one previous item prepared in memory.

#### Examples

- Syntax:
    ```sh
    python -m dotz <file-or-directory>
    ```
- To render a single image:
    ```sh
    python -m dotz path/to/image.jpg
    ```
- To render all images and videos in a directory:
    ```sh
    python -m dotz path/to/directory/
    ```
- To run a slideshow with a custom delay (e.g. 3 seconds):
    ```sh
    python -m dotz -s 3 path/to/directory/
    ```

## Navigation

| Key             | Action   |
|-----------------|----------|
| <kbd>Right</kbd>, <kbd>n</kbd>, <kbd>Space</kbd> | Next     |
| <kbd>Left</kbd>, <kbd>p</kbd>         | Previous |
| <kbd>Up</kbd>              | First    |
| <kbd>Down</kbd>            | Last     |
| <kbd>s</kbd>, <kbd>S</kbd>            | Toggle forward/reverse slideshow |
| <kbd>+</kbd>, <kbd>-</kbd>, <kbd>0</kbd>         | Zoom in, zoom out, zoom reset |
| <kbd>h</kbd>, <kbd>j</kbd>, <kbd>k</kbd>, <kbd>l</kbd>      | Pan left, down, up, right while zoomed |
| <kbd>r</kbd>               | Rotate clockwise |
| <kbd>f</kbd>               | Flip horizontally |
| <kbd>i</kbd>               | Show file metadata |
| <kbd>d</kbd>, <kbd>D</kbd>            | Decrease/increase slideshow delay by 1 sec |
| <kbd>[</kbd>, <kbd>]</kbd>            | Seek backward/forward in a video by the current seek step |
| <kbd>{</kbd>, <kbd>}</kbd>            | Decrease/increase the video seek step: 1, 2, 5, 10, or 30 sec |
| <kbd>,</kbd>, <kbd>.</kbd>            | Move to the previous/next 0.2 sec video preview frame |
| <kbd>v</kbd>               | Toggle a lightweight 5 fps video preview |
| <kbd>q</kbd>, <kbd>Esc</kbd>          | Quit     |
| <kbd>?</kbd>               | Show keyboard help |

The two-line status bar shows the current item and filename first, followed by zoom, slideshow, and video state on the second line.

## Dependencies

| Package   | Version    | Usage                                      |
|-----------|------------|--------------------------------------------|
| python    | >=3.7      | Required Python version                    |
| numpy     | >=1.20     | Fast array operations for image processing |
| Pillow    | >=8.0      | Image loading and manipulation             |
| ffmpeg    | >=4.2      | Video frame extraction                     |

## Formats

**Image:** PNG, JPG, JPEG, BMP, GIF, TIFF, WEBP

**Video:** MP4, MKV, AVI, MOV, WEBM, FLV, WMV, MPEG, MPG

## License

MIT
