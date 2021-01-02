import requests
from pathlib import Path
from tinytag import TinyTag
import os
import logging
from PIL import Image, ImageFont, ImageDraw
import ffmpeg
import shutil

"""Size of canvas for PIL, set to 2k/1440p"""
SIZE = (2560, 1440)

"""Background colour of canvas"""
BG_COLOUR = (12, 27, 51)

"""Text colour of canvas"""
TEXT_COLOUR = (255, 255, 255)

"""URL to tagging api (tagzen)"""
API_TAG_URL = "https://tagzen.ogriffiths.com"

"""Starting position of song in pixels away from the left"""
SONG_X_POS = 300

"""Starting position of song in pixels away from the top"""
SONG_Y_POS = 300

"""Optional additional spacing for the y position of the song away from other songs"""
SONG_Y_SPACING = 0

"""Symbol to use for the active song"""
ACTIVE_SYMBOL = "→"

"""Path to music files"""
MUSIC_PATH = Path("./music/")

"""Path to temp images"""
TMP_PATH = Path("./tmp/")

"""Path to output playlist"""
PLAYLIST_PATH = Path("./playlist.mp4")


class Song:
    """A single song"""

    def __init__(self, path: Path):
        self.file_path = path

        if not path.exists():
            logging.warn(f"Song '{path}' does not exist!")

        audio = TinyTag.get(path)
        payload = {
            "name": f"{audio.title}{path.suffix}"
            if audio.title and path.suffix
            else path
        }

        if audio.artist:
            payload["artist"] = audio.artist

        if audio.album:
            payload["album"] = audio.album

        resp = requests.post(f"{API_TAG_URL}/music/song", params=payload)

        if resp.status_code != 200:
            raise Exception(f"API failed when trying to tag '{path}' song!")

        song_dict = resp.json()["body"]

        self.name = song_dict["name"]
        self.render = song_dict["render"]
        self.render_active = "• " + song_dict["render"]
        self.ext = song_dict["ext"]
        self.artist = song_dict["artist"]
        self.album = song_dict["album"]

    def __repr__(self):
        return self.render


playlist_name = input("Name for this playlist\n> ")
playlist_image = input(
    "Path to the image of this playlist, this should be 2560x1440. You may leave this\noption blank to choose a background colour.\n> "
)

if playlist_image == "":
    tmp_colour = input(
        "Hex code for the background colour of this playlist, you may leave this empty\nfor the default playlist colour.\n> "
    )

    playlist_bg_colour = (
        BG_COLOUR
        if tmp_colour == ""
        else (
            int(tmp_colour[:2], 16),
            int(tmp_colour[2:4], 16),
            int(tmp_colour[4:6], 16),
        )
    )

print("Collecting songs ..")

if not MUSIC_PATH.exists():
    logging.info(f"Directory for music input {MUSIC_PATH} does not exist, creating ..")
    os.mkdir(MUSIC_PATH)

if not TMP_PATH.exists():
    logging.info(f"Directory for temp images {TMP_PATH} does not exist, creating ..")
    os.mkdir(TMP_PATH)

songs = []
_, _, files = next(os.walk(MUSIC_PATH))

for file in sorted(files):
    image_path = MUSIC_PATH / Path(file)
    logging.info(f"Getting metadata for {image_path} song ..")

    songs.append(Song(image_path))

title_font = ImageFont.truetype(
    "/usr/share/fonts/truetype/hack/Hack-Bold.ttf", 75, encoding="unic"
)

body_font = ImageFont.truetype(
    "/usr/share/fonts/truetype/hack/Hack-Regular.ttf", 40, encoding="unic"
)

body_bold_font = ImageFont.truetype(
    "/usr/share/fonts/truetype/hack/Hack-Bold.ttf", 55, encoding="unic"
)


def calc_song_h(ind: int) -> int:
    """Calculates y pos of song"""

    return SONG_Y_POS + (50 * ind) + (ind * SONG_Y_SPACING)


print("Rendering songs ..")

for active_ind, song_active in enumerate(songs):
    logging.info(f"Rendering image for active '{song_active.file_path}' song ..")

    if playlist_image == "":
        image = Image.new("RGB", SIZE, color=playlist_bg_colour)
    else:
        image = Image.open(playlist_image)

    draw = ImageDraw.Draw(image)

    draw.text(
        (SONG_X_POS - 5, SONG_Y_POS - 100), playlist_name, TEXT_COLOUR, font=title_font
    )

    for cur_ind, cur_song in enumerate(songs):
        song_h = calc_song_h(cur_ind)  # height of song
        draw.text((SONG_X_POS, song_h), cur_song.render, TEXT_COLOUR, font=body_font)

        if cur_song == song_active:
            draw.text(
                (SONG_X_POS - 65, song_h - 11.5),
                ACTIVE_SYMBOL,
                TEXT_COLOUR,
                font=body_bold_font,
            )

    song_active.image_path = TMP_PATH / Path(f"{active_ind}.png")
    logging.info(
        f"Saving '{song_active.file_path}' image to '{song_active.image_path}' .."
    )
    image.save(song_active.image_path)

print("Rendering final video ..")

if PLAYLIST_PATH.exists():
    logging.info(f"Deleting '{PLAYLIST_PATH}' old playlist")
    os.remove(PLAYLIST_PATH)

videostream = []

for song in songs:
    videostream.append(ffmpeg.input(str(song.image_path)))
    videostream.append(ffmpeg.input(str(song.file_path)))

ffmpeg.concat(*videostream, v=1, a=1).output(str(PLAYLIST_PATH), r=0.5, ab=256000).run()

if TMP_PATH.exists():
    logging.info(f"Deleting '{TMP_PATH}' temp directory ..")
    shutil.rmtree(TMP_PATH)

print(f"Finished! Find your playlist at:\n\n{PLAYLIST_PATH.resolve()}")
