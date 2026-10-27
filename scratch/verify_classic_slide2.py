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

        # Advance to Slide 2
        await page.keyboard.press("ArrowRight")
        await page.wait_for_timeout(400)
        await page.screenshot(path=f"{out_dir}/slide2_classic_default.png")
        print("Captured Slide 2: Classic 4-Character Slots (Default)")

        # Hover over Hermione
        await page.hover('.character-slot[data-character="hermione"]')
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{out_dir}/slide2_classic_hover_hermione.png")
        print("Captured Slide 2: Hover Hermione")

        # Click Quirrell
        await page.click('.character-slot[data-character="quirrell"]')
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{out_dir}/slide2_classic_click_quirrell.png")
        print("Captured Slide 2: Click Quirrell (Selected)")

        await browser.close()
        print("Done classic slide 2 verification!")

asyncio.run(run())
