"""Generate app icon: split page (简约分页图标)"""
from PIL import Image, ImageDraw

SIZES = [16, 32, 48, 64, 128, 256]
BLUE = (37, 99, 235)
BLUE_DARK = (29, 78, 216)


def generate_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = max(2, size // 6)
    gap = max(1, size // 16)
    page_w = (size - 2 * margin - gap) // 2
    page_h = size - 2 * margin
    cy = size // 2

    cx_left = margin + page_w // 2
    cx_right = size - margin - page_w // 2

    r = max(1, page_w // 5)
    draw.rounded_rectangle(
        [cx_left - page_w // 2, cy - page_h // 2, cx_left + page_w // 2, cy + page_h // 2],
        radius=r, fill=BLUE
    )
    draw.rounded_rectangle(
        [cx_right - page_w // 2, cy - page_h // 2, cx_right + page_w // 2, cy + page_h // 2],
        radius=r, fill=BLUE_DARK
    )

    return img


def main():
    img = generate_icon(256)
    img.save("resources/icon.ico", format="ICO", sizes=[(s, s) for s in SIZES])
    print("Icon saved to resources/icon.ico")


if __name__ == "__main__":
    main()
