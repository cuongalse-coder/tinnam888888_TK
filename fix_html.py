import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace return html in generate_form_html
content = content.replace(
    '        html += "</div></div>"\n        return html\n\n    def generate_item_cards_html',
    '        html += "</div></div>"\n        html = "\\n".join(line.strip() for line in html.split("\\n"))\n        return html\n\n    def generate_item_cards_html'
)

# And also for generate_item_cards_html just in case we ever use markdown for it
content = content.replace(
    '            html += "</div></div>"\n        return html\n\n    tabs = st.tabs',
    '            html += "</div></div>"\n        html = "\\n".join(line.strip() for line in html.split("\\n"))\n        return html\n\n    tabs = st.tabs'
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
