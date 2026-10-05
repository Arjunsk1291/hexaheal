"""Dashboard screenshots with Playwright (desktop + mobile). Needs `npx vite preview --port 4173` in dashboard/."""
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, vp in [("desktop", {"width": 1440, "height": 900}), ("mobile", {"width": 390, "height": 844})]:
        pg = b.new_page(viewport=vp); pg.goto("http://localhost:4173/", wait_until="load"); pg.wait_for_timeout(1500)
        pg.screenshot(path=f"docs/screenshots/dashboard_{name}.png", full_page=True)
    b.close()
print("shots ok")
