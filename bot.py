import requests
import json
import praw
from collections import defaultdict
from bs4 import BeautifulSoup
from selenium import webdriver
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
from datetime import date
from dotenv import load_dotenv
from os.path import join, dirname

env_path = join(dirname(__file__), '.env')
load_dotenv(env_path)

reddit = praw.Reddit(
    client_id=os.environ.get('reddit_ci'),
    client_secret=os.environ.get('reddit_cs'),
    user_agent=os.environ.get('reddit_ua')
)

def get_weather():
    api_key = os.environ.get('weather_api_key')
    res = requests.get(f'http://dataservice.accuweather.com/forecasts/v1/hourly/1hour/3193_PC?apikey={api_key}')
    weather = res.json()
    result = {}
    for data in weather:
        result.update({'datetime': data['DateTime'], 'raining': str(data['HasPrecipitation']), 'temperature': str(data['Temperature']['Value']) + data['Temperature']['Unit']})
    return result

def get_nba_scores():
    new_url = 'http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard'
    r = requests.get(new_url)
    foot = r.json()
    data = foot["events"][0]["competitions"][0]["competitors"]
    scores = {}
    for i in data:
        temp = json.dumps({'team': i['team']['displayName'], 'score': i['score']})
        scores.setdefault('items', []).append(temp)
    return scores

def get_nfl_scores():
    new_url = 'http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard'
    r = requests.get(new_url)
    foot = r.json()
    data = foot["events"][0]["competitions"][0]["competitors"]
    scores = {}
    for i in data:
        temp = json.dumps({'team': i['team']['displayName'], 'score': i['score']})
        scores.setdefault('items', []).append(temp)
    return scores


def get_medium_posts(query):
    url = f'https://medium.com/search?q={query}'
    driver = webdriver.Chrome(os.environ.get('chrome_driver'))
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    data = soup.find('div', class_="u-maxWidth600 js-postList")
    posts = {}
    for x in data:
        sections = x.find_all('div', class_="u-paddingTop20 u-paddingBottom25 u-borderBottomLight js-block")
        for j in sections:
            article = j.find('div', class_="postArticle-content")
            article_readmore = j.find('div', class_="postArticle-readMore")
            #print(article)
            for i in article:
                title = i.find('h3').text
            for url in article_readmore.find_all('a', href=True):
                temp = json.dumps({'title': title, 'url': url['href']})
                posts.setdefault('items', []).append(temp)
    
    return posts
            

def get_reddit_posts():
    topics = ['golang', 'node', 'python']
    data = {}
    for i in topics:
        subreddit = reddit.subreddit(i)
        for submission in subreddit.top(limit=5):
            temp = json.dumps({'title': submission.title, 'url': submission.url})
            data.setdefault('items', []).append(temp)
    return data

def send_mail(datetime, weather, basketball_data, football_data, medium_data, reddit_data):
    msg = MIMEMultipart('alternative')
    me = os.environ.get('email_me')
    to = os.environ.get('email_to')
    msg['subject'] = "Your Morning Briefing"
    msg['From'] = 'Jarvis'
    msg['To'] = to
    text = "Good Morning! Here's your morning briefing"
    basketball_string =""
    for x in basketball_data:
        basketball_string += (f'<div>{x["team"]}: {x["score"]}</div>')

    football_string = ""
    for x in football_data:
        football_string += f'<div>{x["team"]}: {x["score"]}</div>'
 
    medium_posts = ""
    for x in medium_data:
        medium_posts += (f'<H4><a style="margin-right:10px" href={x["url"]}>{x["title"]}</a></H4>')
    
    reddit_posts = ""
    for x in reddit_data:
        reddit_posts += (f'<div><H4>{x["title"]}</H4><img src={x["url"]} width="50" height="50"></img></div>')
 
    html = f"""\
        <html>
        <head></head>
        <body> 
        <center>
        <H1> Good Morning! Here's your morning briefing </H1>
        <H2> 
        It is {datetime}. The weather is currently {weather}
        </H2>
        </center>
        <H2> NBA SCORES:  </H3>
        <div>
        {basketball_string}
        </div>
        <H2> NFL SCORES: </H3>
        <div>
        {football_string}
        </div>
        <H2> Medium Articles </H2>
        <div>
        {medium_posts}
        </div>
        <H2> Reddit Posts </H2>
        <div>
        {reddit_posts}
        </div>
        </body>
        </html>
        """ 
    part1 = MIMEText(text, 'plain')
    part2 = MIMEText(html, 'html')
    msg.attach(part1)
    msg.attach(part2)
    mail = smtplib.SMTP('smtp.gmail.com', 587)
    mail.ehlo()
    mail.starttls()
    mail.login(me, os.environ.get('pwd'))
    mail.sendmail(me, to, msg.as_string())
    mail.quit()


def run():
    weather = get_weather()
    today = date.today()
    datetime = today.strftime("%d/%m/%Y")
    temp = weather['temperature']
    basketball = get_nba_scores()
    basketball_data = []
    for x in basketball['items']:
        obj = json.loads(x)
        basketball_data.append(obj)
    football = get_nfl_scores()
    football_data = []
    for i in football['items']:
        obj = json.loads(i)
        football_data.append(obj)

    medium_posts = get_medium_posts('python')
    medium_data = []
    for j in medium_posts['items']:
        medium_data.append(json.loads(j))

    reddit_posts = get_reddit_posts()    
    reddit_data = []
    for x in reddit_posts['items']:
        obj = json.loads(x)
        reddit_data.append(obj)
    send_mail(datetime, temp, basketball_data, football_data, medium_data, reddit_data)
    print('done')


if __name__ == "__main__":
    run()
