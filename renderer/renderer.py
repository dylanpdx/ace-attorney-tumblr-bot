# import sys
import objection_engine
from objection_engine.beans.comment import Comment
import os
import requests
import tempfile
import shutil
import boto3
from celery import Celery
app = Celery('renderer')

AWS_BUCKET_NAME = os.environ['AWS_BUCKET_NAME']
AWS_ENDPOINT_URL = os.environ['AWS_ENDPOINT_URL']
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
BUCKET_FILE_DOMAIN = os.environ['BUCKET_FILE_DOMAIN']

s3 = boto3.client('s3',
    endpoint_url = AWS_ENDPOINT_URL,
    aws_access_key_id = AWS_ACCESS_KEY_ID,
    aws_secret_access_key = AWS_SECRET_ACCESS_KEY
)

os.environ['oe_sentiment_model'] = 'polyglot'

@app.task
def render_comments(request):
    comments = convert_messages_to_objection_engine(request["messages"])
    lastPostId=str(request["lastPostId"])
    lastPostBlogname=request["lastPostBlogname"]

    vidKey = f"v/{lastPostBlogname}/{lastPostId}.mp4"
    # check if bucket already has the file using head_object
    try:
        s3.head_object(Bucket=AWS_BUCKET_NAME, Key=vidKey)
    except:
        pass
    else:
        print("[Renderer] File already exists: "+vidKey)
        return {"url":BUCKET_FILE_DOMAIN + f"/{vidKey}"}

    objection_engine.renderer.render_comment_list(comments,output_filename=f"{lastPostId}.mp4")

    # upload to s3
    s3.upload_fileobj(open(f"{lastPostId}.mp4", 'rb'), AWS_BUCKET_NAME, vidKey)

    # delete the file
    os.remove(f"{lastPostId}.mp4")

    return {"url":BUCKET_FILE_DOMAIN + f"/{vidKey}"}

# download url to temp dir. if the DL is successful, return the path to the file, otherwise return None
def download_evidence_url(url):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            shutil.copyfileobj(response.raw, tmp_file)
            return tmp_file.name
    return None


def convert_messages_to_objection_engine(messages):
    out = []
    for msg in messages:
        if msg['img'] is not None and msg['img'].startswith('http'):
            msg['img'] = download_evidence_url(msg['img'])
        msg["text"] = msg["text"].replace("\n", " ")
        out.append(objection_engine.comment.Comment(text_content=msg['text'], user_name=msg['author'],evidence_path=msg['img']))
    return out