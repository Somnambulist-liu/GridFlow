"""Generate GridFlow brand assets: app icon + QSS check mark."""
from PIL import Image, ImageDraw

SIZES = [16, 32, 48, 64, 128, 256]
BLUE = (37, 99, 235)
BLUE_LIGHT = (96, 165, 250)
TEAL = (20, 184, 166)
WHITE = (255, 255, 255)

# 复选框的选中态勾选标记（画大后缩小的抗锯齿做法）
CHECK_SIZE = 14
CHECK_SUPERSAMPLE = 8
CHECK_STROKE = 2.2
# 勾的颜色跟随主题主色：浅色主题一个资源、深色主题一个资源
CHECK_ASSETS = {
    "check.png": (37, 99, 235),        # LIGHT_COLORS["PRIMARY"]
    "check_dark.png": (59, 130, 246),  # DARK_COLORS["PRIMARY"]
}


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


def generate_check(size=CHECK_SIZE, color=WHITE):
    """复选框选中态用的勾：透明底，颜色由主色决定，先超采样再缩小以获得平滑边缘。"""
    scale = CHECK_SUPERSAMPLE
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    w = max(1, int(CHECK_STROKE * scale))
    pts = [(0.22 * big, 0.54 * big), (0.42 * big, 0.73 * big), (0.79 * big, 0.28 * big)]
    draw.line(pts, fill=color + (255,), width=w, joint="curve")
    for x, y in (pts[0], pts[2]):
        draw.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=color + (255,))
    return img.resize((size, size), Image.LANCZOS)


def main():
    img = generate_icon(256)
    img.save("resources/icon.ico", format="ICO", sizes=[(s, s) for s in SIZES])
    img.save("resources/icon.png", format="PNG")
    print("GridFlow icon saved to resources/icon.ico / icon.png")

    for name, color in CHECK_ASSETS.items():
        generate_check(color=color).save(f"resources/{name}", format="PNG")
        print(f"Check mark saved to resources/{name}")


if __name__ == "__main__":
    main()
