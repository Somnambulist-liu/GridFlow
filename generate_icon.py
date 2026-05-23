"""Generate GridFlow icon: 2x2 grid cells with flow"""
from PIL import Image, ImageDraw

SIZES = [16, 32, 48, 64, 128, 256]
BLUE = (37, 99, 235)
BLUE_LIGHT = (96, 165, 250)
TEAL = (20, 184, 166)
WHITE = (255, 255, 255)


def generate_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = max(1, size // 8)
    gap = max(1, size // 20)
    cell_w = (size - 2 * pad - gap) // 2
    cell_h = (size - 2 * pad - gap) // 2
    r = max(1, cell_w // 5)

    # 2x2 grid with different shades (top-left to bottom-right flow)
    cells = [
        (pad, pad, BLUE),                                    # top-left
        (pad + cell_w + gap, pad, BLUE_LIGHT),               # top-right
        (pad, pad + cell_h + gap, BLUE_LIGHT),               # bottom-left
        (pad + cell_w + gap, pad + cell_h + gap, TEAL),      # bottom-right
    ]

    for x, y, color in cells:
        draw.rounded_rectangle(
            [x, y, x + cell_w, y + cell_h],
            radius=r, fill=color
        )

    return img


def main():
    img = generate_icon(256)
    img.save("resources/icon.ico", format="ICO", sizes=[(s, s) for s in SIZES])
    print("GridFlow icon saved to resources/icon.ico")


if __name__ == "__main__":
    main()
