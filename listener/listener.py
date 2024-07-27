import pytumblr2
import re
import time
from celery import Celery
import threading
import signal
import redis
import os
app = Celery('listener')

# Config
TUMBLR_CONSUMER_KEY = os.environ['TUMBLR_CONSUMER_KEY']
TUMBLR_CONSUMER_SECRET = os.environ['TUMBLR_CONSUMER_SECRET']
TUMBLR_OAUTH_TOKEN = os.environ['TUMBLR_OAUTH_TOKEN']
TUMBLR_OAUTH_TOKEN_SECRET = os.environ['TUMBLR_OAUTH_TOKEN_SECRET']
TUMBLR_BLOG_NAME = os.environ['TUMBLR_BLOG_NAME']
WEB_DOMAIN = os.environ['WEB_DOMAIN']
THUMBNAIL_URL = os.environ['THUMBNAIL_URL']

NOTIF_CHECK_INTERVAL = int(os.environ['NOTIF_CHECK_INTERVAL'])
COMPLETED_TASKS_CHECK_INTERVAL = int(os.environ['COMPLETED_TASKS_CHECK_INTERVAL'])


# wait for celery broker to be ready
print("[Listener] Waiting for broker to be ready")
while True:
    try:
        app.control.inspect().ping()
        break
    except:
        time.sleep(1)
print("[Listener] Broker is ready")

current_tasks = []
lastNotif = int(time.time())

client = pytumblr2.TumblrRestClient(
    TUMBLR_CONSUMER_KEY,
    TUMBLR_CONSUMER_SECRET,
    TUMBLR_OAUTH_TOKEN,
    TUMBLR_OAUTH_TOKEN_SECRET,
)
client.npf_consumption_on()

run = True

def handler_stop_signals(signum, frame):
    global run
    run = False

signal.signal(signal.SIGINT, handler_stop_signals)
signal.signal(signal.SIGTERM, handler_stop_signals)

def get_blog_name_from_npf(npf):
    if 'blog' in npf:
        author = npf['blog']['name']
    elif 'broken_blog_name' in npf:
        author = npf['broken_blog_name']
    else:
        author = "Anonymous"
    return author

def convert_npf_to_messages(npf):
    messages = []
    img = None
    text= "..."

    ask=None

    if 'layout' in npf:
        for layout in npf['layout']:
            if layout['type'] == 'ask':
                ask = layout

    if 'content' in npf:
        i=0
        for content in npf['content']:
            author = None
            if ask is not None and i in ask['blocks']:
                if 'attribution' in ask and 'blog' in ask['attribution']: 
                    author = ask['attribution']['blog']['name']
                else:
                    author = "Anonymous"
            else:
                author = get_blog_name_from_npf(npf)

            author = re.sub(r'(-deactivated.*)', '', author)

            if content['type'] == 'image':
                img = content['media'][0]['url']
            elif content['type'] == 'text':
                text = content['text']
                messages.append({"text": text, "img": img,"author": author})
                img = None
                text = "..."
            i += 1
        
        if img is not None:
            messages.append({"text": text, "img": img, "author": author})
        
    return messages
import json
def handle_new_post(postUser,postId):
    post = client.get_single_post(postUser, postId)
    thread = post['trail']
    lastPostId = thread[-1]["post"]["id"]
    lastPostBlogname = get_blog_name_from_npf(thread[-1])
    if len(thread) <= 2: # ignore very short threads
        print("[Listener] Ignoring short thread")
        return
    messages = []
    
    for npf in thread:
        messages += convert_npf_to_messages(npf)
    for message in messages:
        if message['author'] == TUMBLR_BLOG_NAME:
            return # ignore threads that have us in them
    task = app.send_task("renderer.render_comments", args=[{"messages":messages,"lastPostId":lastPostId,"lastPostBlogname":lastPostBlogname}])
    current_tasks.append({"task": task, "postId": postId, "postUser": postUser,"lastPostId":lastPostId,"lastPostBlogname":lastPostBlogname})

def check_new_notifs():
    global lastNotif
    clientnotifs = client.notifications(TUMBLR_BLOG_NAME,type='user_mention')
    notifs=clientnotifs['notifications']

    before = clientnotifs["_links"]["next"]["query_params"]["before"]
    # check if more notifs need to be fetched
    while int(before) > lastNotif:
        print("[Listener] Fetching more notifs")
        clientnotifs = client.notifications(TUMBLR_BLOG_NAME,type='user_mention',before=before)
        notifs+=clientnotifs['notifications']
        before = clientnotifs["_links"]["next"]["query_params"]["before"]

    #print("got "+str(len(notifs))+" new notifs")
    # remove any that are older than the last notif
    notifs = [notif for notif in notifs if notif['timestamp'] > lastNotif]
    print("[Listener] Got "+str(len(notifs))+" new notifs after filtering")

    highest_ts = 0
    for notif in notifs:
        postUser = notif['target_tumblelog_name']
        postId = notif['target_post_id']
        notifTime = notif['timestamp']
        if notifTime <= lastNotif:
            continue

        try:
            handle_new_post(postUser,postId)
        except Exception as e:
            print("error handling post: "+str(e))
        if notifTime > highest_ts:
            highest_ts = notifTime
    if highest_ts > lastNotif:
        lastNotif = highest_ts
    
# Thread that handles completed tasks
def handle_completed_tasks():
    global current_tasks
    for qtask in current_tasks:
        if qtask['task'].ready():
            result = qtask['task'].result
            try:
                url = result['url']
                postid = qtask['postId']
                postuser = qtask['postUser']
                lastPostId = qtask['lastPostId']
                lastPostBlogname = qtask['lastPostBlogname']
                pageUrl = f'{WEB_DOMAIN}/{lastPostBlogname}/{lastPostId}'

                reblogPost=client.get_single_post(blogname=postuser, id=postid)
                reblogBlogUUID = reblogPost["blog"]["uuid"]
                reblogPostReblogKey = reblogPost["reblog_key"]
                print("[Listener] Reblogging post "+str(postid)+" from "+str(postuser))
                client.reblog_post(
                    TUMBLR_BLOG_NAME,  # reblogging TO
                    postuser,  # reblogging FROM
                    postid,
                    content=[
                        {'type': 'text', 'text': "Here is your generated video!"},
                        {'type': 'link', 'url': pageUrl, 'title': 'Ace Attorney Video', 'description': 'Ace attourney court video generated from this thread',"poster":[{
                            "url":THUMBNAIL_URL
                        }]},
                    ],
                    tags=["acecourtbot"],
                    parent_blog_uuid=reblogBlogUUID,
                    reblog_key=reblogPostReblogKey
                )
            except Exception as e:
                print("[Listener] Error reblogging: "+str(e))

            current_tasks.remove(qtask)
    if run or len(current_tasks) > 0:
        threading.Timer(COMPLETED_TASKS_CHECK_INTERVAL, handle_completed_tasks).start()
threading.Timer(COMPLETED_TASKS_CHECK_INTERVAL, handle_completed_tasks).start() # start the thread

# Thread that checks for new notifications every minute
def check_for_new_notifs():
    while run:
        check_new_notifs()
        for i in range(NOTIF_CHECK_INTERVAL):
            time.sleep(1)
            if not run:
                break

check_for_new_notifs()