import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(viewport={"width": 1728, "height": 972})
        page = await context.new_page()

        file_url = "file:///Users/nhanvu/Documents/code/book-clone/doc/presentation/pov-graph-slides.html"
        await page.goto(file_url)
        await page.wait_for_timeout(500)

        out_dir = "scratch/verify_shots"

        # Capture Slide 1: Clean Minimalist Title
        await page.screenshot(path=f"{out_dir}/slide1_title_clean.png")
        print("Captured Slide 1: Clean Title")

        # Slide 2: Simple Character Roster (Default)
        await page.keyboard.press("ArrowRight")
        await page.wait_for_timeout(400)
        await page.screenshot(path=f"{out_dir}/slide2_roster_simple_default.png")
        print("Captured Slide 2: Simple Character Roster (Default)")

        # Slide 2: Hover over Harry to reveal attributes
        await page.hover('.simple-char-card[data-char="harry"]')
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{out_dir}/slide2_roster_hover_harry.png")
        print("Captured Slide 2: Hover Harry")

        # Slide 2: Hover over Quirrell to reveal attributes
        await page.hover('.simple-char-card[data-char="quirrell"]')
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{out_dir}/slide2_roster_hover_quirrell.png")
        print("Captured Slide 2: Hover Quirrell")

        # Slide 2: Hover over Snape to reveal attributes
        await page.hover('.simple-char-card[data-char="snape"]')
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{out_dir}/slide2_roster_hover_snape.png")
        print("Captured Slide 2: Hover Snape")

        await browser.close()
        print("Verification completed successfully!")

asyncio.run(run())
