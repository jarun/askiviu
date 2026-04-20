# askiviu

Render images (including animated GIFs) as Braille dot art in the terminal with xterm-256 color and ncurses dim/normal/bold attributes.

## Features
- Braille art rendering for images
- Animated GIF support
- xterm-256 color and grayscale
- Dithering options (ordered, error diffusion)
- Video frame extraction (with ffmpeg)
- Keyboard navigation and slideshow mode

## Example Images

<img width="1323" height="826" alt="image_01" src="https://github.com/user-attachments/assets/f2becbbc-cfeb-42b3-bd92-3882ff3fb570" />
<br><br>
<img width="1333" height="827" alt="image_02" src="https://github.com/user-attachments/assets/62bc16a8-246b-4b5a-a11e-fd0faa5c8066" />
<br><br>
<img width="1301" height="954" alt="image_03" src="https://github.com/user-attachments/assets/609805be-c0c5-4815-bb33-3bc70d69c152" />

## Usage
```sh
python -m askiviu <image-or-directory>
```

- To render a single image:
	```sh
	python -m askiviu path/to/image.jpg
	```
- To render all images and videos in a directory:
	```sh
	python -m askiviu path/to/directory/
	```

## Navigation Keys

- `Right Arrow`, `l`, `Space`: Next image
- `Left Arrow`, `h`: Previous image
- `Up Arrow`: First image
- `Down Arrow`: Last image
- `q`, `Esc`: Quit

## Arguments

- `-S`, `--no-sharpen`: Disable edge sharpening (default: sharpen enabled)
- `-C`, `--no-color`: Disable color (greyscale only; default: color enabled)
- `-d`, `--dither`: Dithering mode (`ordered`, `error`, `none`) (default: `ordered`)
- `-w`, `--wait`: Wait time for slideshow/single image in seconds (default: 5)
- `-s`, `--slideshow`: Enable slideshow mode (default: off)
- `-f`, `--frametime`: Time position (in format HH:MM:SS or seconds) to extract frame from video files (default: 0:0:10)
- `-x`, `--extractformat`: Format for extracted video frames (`jpeg`, `png`) (default: `jpeg`)

## Dependencies

- numpy
- Pillow
- ffmpeg

## License
MIT
