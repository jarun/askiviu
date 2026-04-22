# dot

Render images and video previews as Braille dot art in the terminal with xterm-256 color and ncurses dim/normal/bold attributes.

## Features

- Braille art rendering for images
- Animated GIF support
- xterm-256 color and grayscale
- Dithering options (ordered, error diffusion)
- Video frame extraction (with ffmpeg)
- Keyboard navigation and slideshow mode

<br>
<img width="1323" height="826" alt="image_01" src="https://github.com/user-attachments/assets/f2becbbc-cfeb-42b3-bd92-3882ff3fb570" />
<br><br>
<img width="1333" height="827" alt="image_02" src="https://github.com/user-attachments/assets/62bc16a8-246b-4b5a-a11e-fd0faa5c8066" />
<br><br>
<img width="1301" height="954" alt="image_03" src="https://github.com/user-attachments/assets/609805be-c0c5-4815-bb33-3bc70d69c152" />


## Installation

Install the required dependencies and the dot command:

```sh
# Install system dependencies (e.g., ffmpeg)
sudo apt-get install ffmpeg  # or use your OS package manager

# Install Python dependencies and the CLI tool
sudo pip3 install .
```

After installation, you can run the tool using:

```sh
dot [options] <file-or-directory>
```

## Usage

```
usage: dot [-h] [-S] [-C] [-d {ordered,error,none}] [-s [DELAY]] [-k SEEK] [-f {jpeg,png}] [path]

Render an image or all images/videos in a directory as Braille dots using ncurses with optional xterm-256 color.

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

#### Examples

- Syntax:
    ```sh
    python -m dot <file-or-directory>
    ```
- To render a single image:
    ```sh
    python -m dot path/to/image.jpg
    ```
- To render all images and videos in a directory:
    ```sh
    python -m dot path/to/directory/
    ```
- To run a slideshow with a custom delay (e.g. 3 seconds):
    ```sh
    python -m dot -s 3 path/to/directory/
    ```

## Navigation

| Key             | Action   |
|-----------------|----------|
| Right, l, Space | Next     |
| Left, h         | Previous |
| Up              | First    |
| Down            | Last     |
| s               | Toggle slideshow |
| q, Esc          | Quit     |

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
