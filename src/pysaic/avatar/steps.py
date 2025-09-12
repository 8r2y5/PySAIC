import logging
from functools import partial
from pathlib import Path
from typing import Optional
from xml.etree.ElementTree import Element, ElementTree, SubElement, indent

from PIL import Image, ImageFilter

from pysaic.avatar.layer_modes import (
    calculate_gimp_multiply_pixel,
    do_add_mode,
    do_merge_mode,
    do_soft_light_mode,
)
from pysaic.settings import avatar_images_path

logger = logging.getLogger(__name__)


def generate_xml_config(gamedata_path: Optional[Path] = None) -> None:
    w_element = Element("w")
    tree = ElementTree(w_element)
    file_element = SubElement(w_element, "file", {"name": "ui\pysaic_player"})
    avatar = Element(
        "texture",
        {
            "id": "pysaic_icon_player",
            "x": "0",
            "y": "0",
            "width": "126",
            "height": "56",
        },
    )
    file_element.append(avatar)
    indent(tree, space="\t", level=0)  # game does not understand one line xml
    filename = (
        (Path("gamedata") if not gamedata_path else gamedata_path)
        / "configs"
        / "ui"
        / "textures_descr"
        / "pysaic_icon_player.xml"
    )
    logger.info('"Generating XML config file %s"', filename)
    filename.parent.mkdir(parents=True, exist_ok=True)
    tree.write(
        filename,
        encoding="windows-1251",  # game does not understand utf-8
        xml_declaration=True,
        method="xml",
    )


def combine_images(
    base_image: Image.Image,
    overlay_image: Image.Image,
    merge_function: callable,
) -> Image.Image:
    """
    Merges the RGB values of the overlay image into the base image.
    """
    width, height = base_image.size
    result_image = base_image.copy()
    for x in range(width):
        for y in range(height):
            base_pixel = base_image.getpixel((x, y))
            overlay_pixel = overlay_image.getpixel((x, y))

            # Merge RGB values using the provided function
            merged_pixel = tuple(merge_function(base_pixel, overlay_pixel))
            result_image.putpixel((x, y), merged_pixel)

    return result_image


def add_stripes(composite_image: Image.Image) -> Image.Image:
    composite_image = Image.blend(
        composite_image,
        Image.open(avatar_images_path / "rgb_stripes.png").convert("RGBA"),
        alpha=0.03,
    )
    return combine_images(
        composite_image,
        Image.open(avatar_images_path / "rgb_stripes.png").convert("RGBA"),
        # partial(do_apply_blend, power=0.01),
        partial(do_merge_mode, power=0.05),
        # partial(calculate_gimp_multiply_pixel, opacity=0.01)
    )


def add_pysaic_logo(composite_image):
    # pysaic logo soft light
    pysaic_logo = Image.open(avatar_images_path / "pysaic text.png").convert(
        "RGBA"
    )
    # it looks a lot better than dots blured by this method
    pysaic_logo_blured = pysaic_logo.filter(
        ImageFilter.GaussianBlur(radius=1.5)
    )
    composite_image = combine_images(
        composite_image, pysaic_logo_blured, do_soft_light_mode
    )

    return combine_images(
        composite_image,
        pysaic_logo,
        partial(do_add_mode, power=0.2),
    )


def add_dots(composite_image):
    # dots add mode
    dots = Image.open(avatar_images_path / "dots.png").convert("RGBA")

    # this is a workaround for the fact that PIL does not support
    # ImageFilter.GaussianBlur on RGBA images with alpha channel
    # dots_blured  = dots.filter(ImageFilter.GaussianBlur(radius=1.5))
    # they look ugly and have artifacts, so we use a pre-rendered image
    dots_blured = Image.open(avatar_images_path / "dots_blured.png").convert(
        "RGBA"
    )

    alpha_band = dots_blured.split()[3]
    dots_blured.putalpha(
        alpha_band.point(
            lambda p: int(
                p
                * 0.2  # power/opacity of the blur effect, 0.2 is a good value
            )
        )
    )
    composite_image = Image.alpha_composite(composite_image, dots_blured)

    # dots soft light
    return combine_images(
        composite_image, dots, partial(do_soft_light_mode, power=1)
    )


def add_secret_text(composite_image):
    # secret "text"
    return combine_images(
        composite_image,
        Image.open(avatar_images_path / "secret text.png").convert("RGBA"),
        partial(do_soft_light_mode, power=1),
    )


def add_watermark(composite_image):
    return combine_images(
        composite_image,
        Image.open(avatar_images_path / "water mark.png").convert("RGBA"),
        partial(calculate_gimp_multiply_pixel, opacity=0.637),
    )


def add_light_shadow(composite_image):
    # light shadow
    return combine_images(
        composite_image,
        Image.open(avatar_images_path / "light shadow.png").convert("RGBA"),
        partial(do_soft_light_mode, power=0.3),
    )


def add_frame(composite_image, frame_image):
    frame_mask = Image.open(avatar_images_path / "frame_mask.png").convert("L")
    composite_image = Image.composite(composite_image, frame_image, frame_mask)
    composite_image.paste(frame_image, (0, 0), frame_image)
    return composite_image
