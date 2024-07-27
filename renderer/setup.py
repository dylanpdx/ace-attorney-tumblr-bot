import sys
import objection_engine
import os
from objection_engine import utils
utils.ensure_assets_are_available()

from objection_engine.renderer import render_comment_list
from objection_engine.beans.comment import Comment
foo = [objection_engine.comment.Comment(text_content='First comment',  user_name="First user"), objection_engine.comment.Comment(text_content='Second comment',  user_name="Second user")]
objection_engine.renderer.render_comment_list(foo)

# delete output.mp4
os.remove('output.mp4')