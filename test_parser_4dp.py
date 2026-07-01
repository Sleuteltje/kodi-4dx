import os
from michsclasses.project_parser import ProjectParser

test_content = """
## Comment
[TRIVIA] REPEAT, IMG:2000
F:/trivia.jpeg
F:/trivia2.jpeg 5000
F:/trivia3.jpeg + F:/trivia.mp3
F:/trivia.mkv
REPEAT F:/theaterwelcome.mkv
"F:/path with spaces/trivia.jpg" 3000 + "F:/music with spaces.mp3"

[PAUSE] REPEAT DURATION:60000 MUSIC:"F:/bg.mp3"
F:/pausescreen.jpeg 5000
F:/letsallgotothelobby.mkv
"""

with open('test.4dp', 'w', encoding='utf-8') as f:
	f.write(test_content)

parser = ProjectParser('test.4dp')
import json
print(json.dumps(parser.get_blocks(), indent=2))
