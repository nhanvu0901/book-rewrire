import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(viewport={"width": 1728, "height": 972})
        page = await context.new_page()

        file_url = "file:///Users/nhanvu/Documents/code/book-clone/doc/presentation/pov-graph-slides.html"
        await page.goto(file_url)
        await page.wait_for_timeout(600)

        out_dir = "scratch/verify_shots"

        # Advance to Slide 2
        await page.keyboard.press("ArrowRight")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{out_dir}/slide2_marvel_default_harry.png")
        print("Captured Slide 2 Marvel Rivals: Default Harry Selected")

        # Hover over Hermione
        await page.hover('#hero-slot-hermione', force=True)
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{out_dir}/slide2_marvel_hover_hermione.png")
        print("Captured Slide 2 Marvel Rivals: Hover Hermione")

        # Hover over Quirrell
        await page.hover('#hero-slot-quirrell', force=True)
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{out_dir}/slide2_marvel_hover_quirrell.png")
        print("Captured Slide 2 Marvel Rivals: Hover Quirrell")

        # Click Ron
        await page.click('#hero-slot-ron', force=True)
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{out_dir}/slide2_marvel_click_ron.png")
        print("Captured Slide 2 Marvel Rivals: Click Ron Selected")

        await browser.close()
        print("Done Marvel Rivals verification!")

asyncio.run(run())
