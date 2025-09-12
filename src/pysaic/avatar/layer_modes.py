import math

RGBA_TUPLE = tuple[int, int, int, int]


def invert_color(value: int | float) -> int:
    """
    Inverts a single RGB color value.
    """
    return int(255 - value)


def do_merge_mode(
    base_rgb: RGBA_TUPLE, overlay_value: RGBA_TUPLE, power=1.0
) -> RGBA_TUPLE:
    """
    Merges RGB values in overlay mode.
    """
    overlay_alpha = overlay_value[3] / 255.0
    r = (
        base_rgb[0]
        * invert_color(invert_color(overlay_value[0] * overlay_alpha) * power)
    ) // 255
    g = (
        base_rgb[1]
        * invert_color(invert_color(overlay_value[1] * overlay_alpha) * power)
    ) // 255
    b = (
        base_rgb[2]
        * invert_color(invert_color(overlay_value[2] * overlay_alpha) * power)
    ) // 255

    return (
        int(r),
        int(g),
        int(b),
        255,  # Keep the alpha channel at full opacity
    )


def _soft_light_blend_core_normalized(
    Ac_norm: float, Bc_norm: float, power_strength: float
) -> float:
    Ac_norm = max(0.0, min(1.0, Ac_norm))
    Bc_norm = max(0.0, min(1.0, Bc_norm))
    power_strength = max(0.0, min(1.0, power_strength))

    if power_strength == 0.0:
        return Bc_norm

    if Ac_norm <= 0.5:
        full_soft_light_R_norm = Bc_norm - (1.0 - 2.0 * Ac_norm) * Bc_norm * (
            1.0 - Bc_norm
        )
    else:
        full_soft_light_R_norm = Bc_norm + (2.0 * Ac_norm - 1.0) * (
            math.sqrt(Bc_norm) - Bc_norm
        )

    R_final_norm = (
        Bc_norm * (1.0 - power_strength)
        + full_soft_light_R_norm * power_strength
    )

    return R_final_norm


def percentage_to_255(value: float) -> int:
    return int(round(max(0.0, min(1.0, value)) * 255.0))


def do_soft_light_mode(
    bottom_rgba: RGBA_TUPLE,
    top_rgba: RGBA_TUPLE,
    layer_opacity: float = 1.0,
    power: float = 1.0,
) -> RGBA_TUPLE:
    """
    Applies a soft light effect to the RGB values. GIMP-style soft light
    """
    top_r_norm = top_rgba[0] / 255.0
    top_g_norm = top_rgba[1] / 255.0
    top_b_norm = top_rgba[2] / 255.0
    top_alpha_norm = top_rgba[3] / 255.0

    bottom_r_norm = bottom_rgba[0] / 255.0
    bottom_g_norm = bottom_rgba[1] / 255.0
    bottom_b_norm = bottom_rgba[2] / 255.0
    bottom_alpha_norm = bottom_rgba[3] / 255.0

    layer_opacity = max(0.0, min(1.0, layer_opacity))
    blended_r_mode_power = _soft_light_blend_core_normalized(
        top_r_norm, bottom_r_norm, power
    )
    blended_g_mode_power = _soft_light_blend_core_normalized(
        top_g_norm, bottom_g_norm, power
    )
    blended_b_mode_power = _soft_light_blend_core_normalized(
        top_b_norm, bottom_b_norm, power
    )

    effective_top_alpha = top_alpha_norm * layer_opacity

    final_r_norm = (
        blended_r_mode_power * effective_top_alpha
        + bottom_r_norm * (1.0 - effective_top_alpha)
    )
    final_g_norm = (
        blended_g_mode_power * effective_top_alpha
        + bottom_g_norm * (1.0 - effective_top_alpha)
    )
    final_b_norm = (
        blended_b_mode_power * effective_top_alpha
        + bottom_b_norm * (1.0 - effective_top_alpha)
    )

    final_alpha_norm = effective_top_alpha + bottom_alpha_norm * (
        1.0 - effective_top_alpha
    )

    return (
        percentage_to_255(final_r_norm),
        percentage_to_255(final_g_norm),
        percentage_to_255(final_b_norm),
        percentage_to_255(final_alpha_norm),
    )


def do_soft_light_mode_inverted(
    base_rgb: RGBA_TUPLE, overlay_value: RGBA_TUPLE, power=1.0
) -> RGBA_TUPLE:
    """
    Applies a soft light effect to the RGB values, inverting the overlay.
    """
    r = int(
        base_rgb[0]
        + (invert_color(overlay_value[0] * power) - 128) * (base_rgb[0] / 255)
    )
    g = int(
        base_rgb[1]
        + (invert_color(overlay_value[1] * power) - 128) * (base_rgb[1] / 255)
    )
    b = int(
        base_rgb[2]
        + (invert_color(overlay_value[2] * power) - 128) * (base_rgb[2] / 255)
    )

    return (
        int(r),
        int(g),
        int(b),
        255,
    )  # Keep the alpha channel at full opacity


def do_add_mode(
    base_rgb: RGBA_TUPLE, overlay_value: RGBA_TUPLE, power=1.0
) -> RGBA_TUPLE:
    """
    Adds the RGB values of the overlay image to the base image.
    """
    overlay_alpha = overlay_value[3] / 255.0
    r = int(base_rgb[0] + (overlay_value[0] * overlay_alpha * power))
    g = int(base_rgb[1] + (overlay_value[1] * overlay_alpha * power))
    b = int(base_rgb[2] + (overlay_value[2] * overlay_alpha * power))

    return (
        r,
        g,
        b,
        255,  # Keep the alpha channel at full opacity
    )


def do_apply_overlay(
    base_rgb: RGBA_TUPLE, overlay_value: RGBA_TUPLE, power=1.0
) -> RGBA_TUPLE:
    """
    Applies an overlay effect to the RGB values.
    """
    overlay_alpha = overlay_value[3] / 255.0
    r = int(base_rgb[0] * (overlay_value[0] * overlay_alpha / 255) * power)
    g = int(base_rgb[1] * (overlay_value[1] * overlay_alpha / 255) * power)
    b = int(base_rgb[2] * (overlay_value[2] * overlay_alpha / 255) * power)

    return (
        r,
        g,
        b,
        255,  # Keep the alpha channel at full opacity
    )


def do_apply_blend(
    base_rgb: RGBA_TUPLE, overlay_value: RGBA_TUPLE, power=1.0
) -> RGBA_TUPLE:
    """
    Blends the RGB values of the overlay image with the base image.
    """
    overlay_alpha = overlay_value[3] / 255.0
    r = int(
        base_rgb[0] * (1 - power) + overlay_value[0] * power * overlay_alpha
    )
    g = int(
        base_rgb[1] * (1 - power) + overlay_value[1] * power * overlay_alpha
    )
    b = int(
        base_rgb[2] * (1 - power) + overlay_value[2] * power * overlay_alpha
    )

    return (
        r,
        g,
        b,
        255,  # Keep the alpha channel at full opacity
    )


def calculate_gimp_multiply_pixel(
    base_pixel_rgba, blend_pixel_rgba, opacity=1.0
):
    br, bg, bb, ba = base_pixel_rgba
    fr, fg, fb, fa = blend_pixel_rgba

    br_norm, bg_norm, bb_norm, ba_norm = (
        br / 255.0,
        bg / 255.0,
        bb / 255.0,
        ba / 255.0,
    )
    fr_norm, fg_norm, fb_norm, fa_norm = (
        fr / 255.0,
        fg / 255.0,
        fb / 255.0,
        fa / 255.0,
    )

    multiplied_r_norm = br_norm * fr_norm
    multiplied_g_norm = bg_norm * fg_norm
    multiplied_b_norm = bb_norm * fb_norm

    effective_fa_norm = fa_norm * opacity

    out_a_norm = effective_fa_norm + ba_norm * (1 - effective_fa_norm)

    if out_a_norm <= 0:
        return (0, 0, 0, 0)

    out_r_norm = (
        multiplied_r_norm * effective_fa_norm
        + br_norm * ba_norm * (1 - effective_fa_norm)
    ) / out_a_norm
    out_g_norm = (
        multiplied_g_norm * effective_fa_norm
        + bg_norm * ba_norm * (1 - effective_fa_norm)
    ) / out_a_norm
    out_b_norm = (
        multiplied_b_norm * effective_fa_norm
        + bb_norm * ba_norm * (1 - effective_fa_norm)
    ) / out_a_norm

    return (
        percentage_to_255(out_r_norm),
        percentage_to_255(out_g_norm),
        percentage_to_255(out_b_norm),
        percentage_to_255(out_a_norm),
    )
