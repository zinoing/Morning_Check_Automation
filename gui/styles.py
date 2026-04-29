# ── Palette ───────────────────────────────────────────────────────────────────
BG_MAIN      = "#F8FAFC"
BG_CARD      = "#FFFFFF"
BG_SIDEBAR   = "#0F172A"
BG_SIDEBAR_H = "#1E293B"   # hover / active
BG_INPUT     = "#F8FAFC"
BG_TOPBAR    = "#FFFFFF"

BORDER       = "#E2E8F0"
BORDER_FOCUS = "#3B82F6"

ACCENT       = "#3B82F6"   # blue
GREEN        = "#22C55E"
AMBER        = "#F59E0B"
RED          = "#EF4444"
TEAL         = "#0D9488"

TEXT_PRIMARY   = "#0F172A"
TEXT_SECONDARY = "#64748B"
TEXT_MUTED     = "#94A3B8"
TEXT_SIDEBAR   = "#CBD5E1"
TEXT_WHITE     = "#FFFFFF"

BTN_RUN_BG     = "#0F172A"
BTN_STOP_BG    = "#FFFFFF"
BTN_STOP_FG    = "#0F172A"
BTN_PUBLISH_BG = "#0F172A"

# ── Fonts ─────────────────────────────────────────────────────────────────────
FONT = "Segoe UI"

def f(size, weight="normal"):
    return (FONT, size, weight)

F_XS   = f(9)
F_SM   = f(10)
F_BASE = f(11)
F_MD   = f(12)
F_LG   = f(13, "bold")
F_XL   = f(16, "bold")
F_2XL  = f(20, "bold")
F_BRAND = f(14, "bold")

# ── Dimensions ────────────────────────────────────────────────────────────────
SIDEBAR_W      = 190
TOPBAR_H       = 52
BOTTOMBAR_H    = 44
RIGHT_PANEL_W  = 300
CARD_RADIUS    = 8
CARD_PAD       = 16
