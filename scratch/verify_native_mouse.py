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

        # Advance to Slide 2
        await page.keyboard.press("ArrowRight")
        await page.wait_for_timeout(500)

        out_dir = "scratch/verify_shots"

        # 1. Hover Hermione
        await page.hover('#hero-slot-hermione', force=True)
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{out_dir}/slide2_native_hermione.png")
        print("Captured native hover Hermione")

        # 2. Click Ron (locks Ron)
        await page.click('#hero-slot-ron', force=True)
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{out_dir}/slide2_native_click_ron.png")
        print("Captured native click Ron")

        # 3. Hover Quirrell while Ron is selected
        await page.hover('#hero-slot-quirrell', force=True)
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{out_dir}/slide2_native_hover_quirrell.png")
        print("Captured native hover Quirrell")

        await browser.close()
        print("Done native mouse test!")

asyncio.run(run())
