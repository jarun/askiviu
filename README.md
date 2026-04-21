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

## Usage

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
| q, Esc          | Quit     |

## Dependencies

| Package  | Usage                                       |
|----------|---------------------------------------------|
| numpy    | Fast array operations for image processing  |
| Pillow   | Image loading and manipulation              |
| ffmpeg   | Video frame extraction                      |

## Arguments

```
-S, --no-sharpen        : Disable edge sharpening (default: sharpen enabled)
-C, --no-color          : Disable color (greyscale only; default: color enabled)
-d, --dither            : Dithering mode (`ordered`, `error`, `none`) (default: `ordered`)
-s, --slideshow [delay] : Enable slideshow mode with optional integer delay in seconds (default: 5)
-k, --seek              : Seek position (in HH:MM:SS or seconds) to extract frame from videos (default: 10)
-f, --format            : Format for extracted video frames (`jpeg`, `png`) (default: `jpeg`)
```

## Formats

**Image:** PNG, JPG, JPEG, BMP, GIF, TIFF, WEBP

**Video:** MP4, MKV, AVI, MOV, WEBM, FLV, WMV, MPEG, MPG

## License

MIT
