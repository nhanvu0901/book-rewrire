import asyncio, os
from playwright.async_api import async_playwright

async def run():
    out_dir = os.path.abspath("scratch/verify_shots")
    os.makedirs(out_dir, exist_ok=True)
    html_url = "file://" + os.path.abspath("doc/presentation/pov-graph-slides.html")

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        
        # Track network requests
        network_requests = []
        page.on("request", lambda r: network_requests.append(r.url))

        await page.goto(html_url, wait_until="networkidle")
        await asyncio.sleep(0.5)

        # Slide 1
        await page.screenshot(path=os.path.join(out_dir, "slide1_title.png"))
        print("Captured Slide 1")

        # Slide 2: Sprint 1 (Draw.io Graph)
        await page.keyboard.press("2")
        await asyncio.sleep(0.8)
        await page.screenshot(path=os.path.join(out_dir, "slide2_sprint1_drawio.png"))
        print("Captured Slide 2 (Sprint 1: Draw.io Graph)")

        # Slide 2: Toggle Story labels
        await page.click("#btn-toggle-labels")
        await asyncio.sleep(0.4)
        await page.screenshot(path=os.path.join(out_dir, "slide2_sprint1_story_labels.png"))
        print("Captured Slide 2 (Sprint 1: Story Labels)")

        # Slide 3: Sprint 2 (Barrier vs Traced Pipeline)
        await page.keyboard.press("3")
        await asyncio.sleep(0.8)
        await page.screenshot(path=os.path.join(out_dir, "slide3_sprint2_barrier_solution.png"))
        print("Captured Slide 3 (Sprint 2: Barrier vs Solution)")

        # Slide 3: Click Simulate Traced Pipeline
        await page.click("#btn-simulate-pipeline")
        await asyncio.sleep(1.5)
        await page.screenshot(path=os.path.join(out_dir, "slide3_sprint2_simulated.png"))
        print("Captured Slide 3 (Sprint 2: After Simulation)")

        # Slide 4: Sprint 3 (Twist Diversion - Ch 16)
        await page.keyboard.press("4")
        await asyncio.sleep(0.8)
        await page.screenshot(path=os.path.join(out_dir, "slide4_sprint3_ch16.png"))
        print("Captured Slide 4 (Sprint 3: Chapter 16)")

        # Slide 4: Click Chapter 17
        await page.click("#btn-chapter-17")
        await asyncio.sleep(0.8)
        await page.screenshot(path=os.path.join(out_dir, "slide4_sprint3_ch17_twist.png"))
        print("Captured Slide 4 (Sprint 3: Chapter 17 Twist)")

        # Slide 5: What's Next for Me
        await page.keyboard.press("5")
        await asyncio.sleep(0.8)
        await page.screenshot(path=os.path.join(out_dir, "slide5_whats_next.png"))
        print("Captured Slide 5 (What's Next for Me)")

        # Check for non-file requests
        non_file = [u for u in network_requests if not u.startswith("file://")]
        print("Non-file requests count:", len(non_file))
        if non_file:
            print("Non-file requests:", non_file)

        await browser.close()

asyncio.run(run())
