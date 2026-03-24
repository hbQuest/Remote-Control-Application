# -*- coding: utf-8 -*-
"""
theme.py - Màu sắc và font chung cho toàn bộ ứng dụng Client
"""

# Bảng màu nhấn nhã (Fluent Design)
ACCENT_BLUE = ("#005FB8", "#60CDFF")   # (Light mode, Dark mode)
ACCENT_RED = ("#D13438", "#FF99A4")
ACCENT_GREEN = ("#107C10", "#6CCB5F")
BG_CARD = ("#FFFFFF", "#2B2B2B")
TEXT_MUTED = ("#5c5c5c", "#a0a0a0")

# Font
FONT_NORMAL = ("Arial", 13)
FONT_BTN = ("Arial", 13, "bold")
FONT_TITLE = ("Arial", 15, "bold")
FONT_HEADER = ("Arial", 12, "bold")
FONT_MONO = ("Consolas", 14)

# Style mặc định cho các nút tính năng trong lưới
def get_feature_btn_style(bg_card, text_muted):
    return {
        "font": FONT_BTN,
        "corner_radius": 8,
        "height": 55,
        "anchor": "w",
        "fg_color": bg_card,
        "text_color": ("black", "white"),
        "hover_color": ("#F0F0F0", "#3E3E42"),
    }
