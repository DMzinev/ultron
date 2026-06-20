import re

with open("c:/Users/This PC/Desktop/cost accounting/ui/appUI.js", "r", encoding="utf-8") as f:
    content = f.read()

# Find functions related to slides or learn mode
matches = re.findall(r"function\s+\w+Slide\w*|function\s+loadLearn\w*|\w+Slide\w*\s*=\s*function|loadLearn\w*\s*=\s*function", content)
print("Function matches:", matches)

# Find references to window.goToLearnSlide
for line_no, line in enumerate(content.splitlines(), 1):
    if "goToLearnSlide" in line or "loadLearnTopic" in line or "session1" in line:
        if line_no < 500 or line_no > 1000: # print some lines
            print(f"{line_no}: {line}")
