import logging
from pathlib import Path
from typing import Optional

from PIL import Image

from pysaic.avatar.steps import (
    add_dots,
    add_frame,
    add_light_shadow,
    add_pysaic_logo,
    add_secret_text,
    add_stripes,
    add_watermark,
    generate_xml_config,
)
from pysaic.settings import GAMEDATA_PATH, avatar_images_path

logger = logging.getLogger(__name__)

if not GAMEDATA_PATH.exists():
    raise FileNotFoundError(
        f"Textures directory does not exists at {GAMEDATA_PATH}."
    )

textures_path = GAMEDATA_PATH / "textures" / "ui"
textures_path = textures_path.resolve().absolute()


def save_avatar(image: Image.Image, png_too: bool = False):
    if not textures_path.exists():
        logger.warning(
            "Textures directory does not exist, creating it at %s",
            textures_path,
        )
        textures_path.mkdir(parents=True)

    if png_too:
        logger.info("Saving composite image as PNG to %s", textures_path)
        image.save(
            textures_path / "pysaic_player.png",
            format="PNG",
            quality=100,
            optimize=True,
            progressive=True,
        )

    # Save the composite image as DDS with DXT5 compression
    logger.info("Saving composite image as DDS to %s", textures_path)
    image.save(
        textures_path / "pysaic_player.dds",
        format="DDS",
        compression="dxt5",
        quality=100,
        progressive=True,
        optimize=True,
        dds_format="DXT5",
        dds_mipmaps=True,
        dds_minimaps=True,
        dds_blur=0,
        dds_filter="kaiser",
        dds_compression_quality=100,
        dds_pixel_format="DXT5",
    )
    generate_xml_config(gamedata_path=GAMEDATA_PATH)


def generate_avatar(
    filename: str | Path | Image.Image,
    png_too=False,
    coordinates: Optional[tuple[int, int, int, int]] = None,
) -> Optional[Image.Image]:
    frame_image = Image.open(avatar_images_path / "frame.png").convert("RGBA")
    if isinstance(filename, Image.Image):
        input_image = filename.crop(coordinates)
    else:
        input_image = Image.open(filename)
    input_image = input_image.convert("RGBA").resize(
        frame_image.size, Image.Resampling.LANCZOS
    )
    composite_image = add_stripes(input_image)
    composite_image = add_pysaic_logo(composite_image)
    composite_image = add_dots(composite_image)
    composite_image = add_secret_text(composite_image)
    composite_image = add_watermark(composite_image)
    composite_image = add_light_shadow(composite_image)
    composite_image = add_frame(composite_image, frame_image)
    if isinstance(filename, Image.Image):
        return composite_image

    save_avatar(composite_image, filename, png_too)


if __name__ == "__main__":
    filename = Path(__file__) / ".." / ".." / "ui" / "pysaic_icon.ico"
    filename = filename.resolve()
    generate_avatar(filename)
