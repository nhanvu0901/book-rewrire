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

        # Evaluate hover hermione
        await page.evaluate("onHeroHover('hermione')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{out_dir}/slide2_eval_hermione.png")
        print("Captured eval hermione")

        # Evaluate hover ron
        await page.evaluate("onHeroHover('ron')")
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{out_dir}/slide2_eval_ron.png")
        print("Captured eval ron")

        await browser.close()

asyncio.run(run())
