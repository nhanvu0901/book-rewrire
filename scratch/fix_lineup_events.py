with open('scratch/build_8_slides.py') as f:
    c = f.read()

# 1. Update lineup container to have onmouseleave="onLineupLeave()"
c = c.replace('<div class="cinematic-lineup-area" id="cinematic-lineup">',
              '<div class="cinematic-lineup-area" id="cinematic-lineup" onmouseleave="onLineupLeave()">')

# 2. Remove onmouseleave="onHeroLeave()" from individual heroes
c = c.replace('onmouseleave="onHeroLeave()"', '')

# 3. In JS, rename onHeroLeave to onLineupLeave
c = c.replace('function onHeroLeave() {', 'function onLineupLeave() {')

with open('scratch/build_8_slides.py', 'w') as f:
    f.write(c)

import subprocess
subprocess.check_call(['python3', 'scratch/build_8_slides.py'])
print("Successfully updated hover events to lineup container!")
