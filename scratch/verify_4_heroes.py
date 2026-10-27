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

        # Capture Slide 1: POV Graph + AI Storytelling from Every Perspective
        await page.screenshot(path=f"{out_dir}/slide1_pov_graph_new.png")
        print("Captured Slide 1: POV Graph")

        # Slide 2: 4 Characters Roster (Default)
        await page.keyboard.press("ArrowRight")
        await page.wait_for_timeout(400)
        await page.screenshot(path=f"{out_dir}/slide2_roster_4_default.png")
        print("Captured Slide 2: 4 Characters Roster (Default)")

        # Slide 2: Hover over Harry
        await page.hover('.simple-char-card[data-char="harry"]')
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{out_dir}/slide2_roster_4_hover_harry.png")
        print("Captured Slide 2: Hover Harry (4 heroes)")

        # Slide 2: Hover over Quirrell
        await page.hover('.simple-char-card[data-char="quirrell"]')
        await page.wait_for_timeout(300)
        await page.screenshot(path=f"{out_dir}/slide2_roster_4_hover_quirrell.png")
        print("Captured Slide 2: Hover Quirrell (4 heroes)")

        await browser.close()
        print("4 Heroes verification completed successfully!")

asyncio.run(run())
