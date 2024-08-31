import streamlit as st
from googleapiclient.discovery import build
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import pymysql
from datetime import datetime

# Initialize the YouTube API client
service_name = "youtube"
version = "v3"
api_key = "AIzaSyDCTKdMatu3aaMV_TmKSaHYrMT_ZVnCm1Q"  # Replace with your actual API key
youtube = build(service_name, version, developerKey=api_key)

# Enhanced TF-IDF setup
categories = ["news", "sports", "food", "fashion", "games"]
corpus = [
    "Breaking news on global events, politics, and social issues.",
    "Live sports updates, scores, highlights, and commentary.",
    "Recipes, food reviews, cooking tips, and culinary trends.",
    "Fashion trends, style guides, clothing reviews, and beauty tips.",
    "Video game news, reviews, gameplay, and industry updates."
]

vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(corpus)

# Function to convert ISO 8601 datetime to MySQL DATETIME format
def convert_to_mysql_datetime(iso_datetime_str):
    if iso_datetime_str:
        try:
            dt = datetime.fromisoformat(iso_datetime_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None
    return None

# Function to fetch video data from YouTube API
def fetch_video_data(video_ids):
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=video_ids
    )
    return request.execute()

# Function to get category based on search query
def get_category_from_query(query, threshold=0.2):
    query_vec = vectorizer.transform([query])
    scores = np.array(X.dot(query_vec.T).toarray()).flatten()
    
    st.write(f"Query: {query}")
    st.write(f"Similarity scores: {scores}")
    
    if max(scores) < threshold:
        st.warning("No strong match found, please refine your search.")
        return None
    
    category_index = np.argmax(scores)
    st.write(f"Selected Category: {categories[category_index]}")  # Show the selected category
    return categories[category_index]

# Database connection
def get_db_connection():
    return pymysql.connect(
        host='localhost',  # or your MySQL server address
        user='root',
        password='Iloveall@12345',
        database='youtube_data'
    )

# Function to insert video data into MySQL
def insert_video_data(video_data):
    connection = get_db_connection()
    cursor = connection.cursor()
    video_id = video_data['id']
    snippet = video_data['snippet']
    statistics = video_data.get('statistics', {})

    title = snippet.get('title', None)
    description = snippet.get('description', None)
    published_at = snippet.get('publishedAt', None)
    duration = video_data.get('contentDetails', {}).get('duration', None)
    view_count = statistics.get('viewCount', None)
    like_count = statistics.get('likeCount', None)
    dislike_count = statistics.get('dislikeCount', None)
    comment_count = statistics.get('commentCount', None)

    published_at_mysql = convert_to_mysql_datetime(published_at)

    sql = """INSERT INTO videos (video_id, title, description, published_at, duration, view_count, like_count, dislike_count, comment_count) 
             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
             ON DUPLICATE KEY UPDATE 
             title=VALUES(title), description=VALUES(description), published_at=VALUES(published_at), duration=VALUES(duration),
             view_count=VALUES(view_count), like_count=VALUES(like_count), dislike_count=VALUES(dislike_count), comment_count=VALUES(comment_count);"""
    
    try:
        cursor.execute(sql, (video_id, title, description, published_at_mysql, duration, view_count, like_count, dislike_count, comment_count))
        connection.commit()
    except pymysql.MySQLError as e:
        st.error(f"An error occurred while inserting data into MySQL: {e}")
    finally:
        cursor.close()
        connection.close()

# Function to fetch and display video data on Streamlit
def fetch_and_display_videos(category):
    video_ids = {
        'news': "LDeM3kvwe2c,nHpAB7r4U0g,8nZ9N3fVMgM,-6fb49zu6L8,jpodQd_3T5c,rXAIJW2YA9E,Tl4w-fEIb2Q,hViJ3SUfTNE,lqAITB1Xt-o,m1RAs9wKRmg",
        'sports': "h_J5rlD4pvo,RJwZ2XzkGW4,PFHi5Y7f60Y,alyWvviZWEs,_6SP4kv1y0s,Iaqs8L2aJSI,eRtkXhCTJVc,g6IccijPdI0,onqlVibRjgs,J8LvdJjJKWQ",
        'food': "nxAMpDUmNR4,bAdnYJfBHmg,O6n0XoNLGi0,3nvw4P5XTqQ,8vk3DJ0GNRk,ZSL_Q6Pe-Ao,wNX8kBThm2s,Zr2t4mYim78,BJjTNhsjO0Q,K2xSnUAM4jk",
        'fashion': "HAOZ_618Sk,6JL4WKa8_A,NmqBprimG3g,DyhjXQn0F0E,tFtYxW1tbF8,OVLpFQHH-CM,pNuGMCH-E9A,BOqMYrbiqUc,fQ1d2YIt-Oo,c_26IN446VQ",
        'games': "pM_rvWwQoqU,FcLaxJbWHZs,LgI1AJoVYuQ,qwjbFpAIXNU,BnlxcS33B60,-ylkr0vhnMA,De6kLq2OFAs,v8H5ACDqlHo,lJrHLnhJl-M,D5tvW00SZFc"
    }

    if category not in video_ids:
        st.error("Invalid category selected.")
        return

    video_ids_str = video_ids[category]
    st.write(f"Fetching videos for category: {category}")
    try:
        response = fetch_video_data(video_ids_str)
        col1, col2 = st.columns([2, 1])
        with col1:
            for video in response['items']:
                snippet = video['snippet']
                video_id = video['id']
                title = snippet.get('title', 'No title')
                description = snippet.get('description', 'No description')
                published_at = snippet.get('publishedAt', 'No date')
                thumbnail_url = snippet.get('thumbnails', {}).get('high', {}).get('url', '')

                st.subheader(title)
                st.image(thumbnail_url, caption=title, use_column_width=True)
                st.write(f"**Published At:** {published_at}")
                st.write(description)
                st.video(f"https://www.youtube.com/watch?v={video_id}")

                # Insert video data into MySQL
                insert_video_data(video)
        with col2:
            st.write("**Video Details:**")
            st.write(f"Showing {len(response['items'])} videos in the category: {category.capitalize()}.")
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Streamlit app layout with custom background color and improved UI
st.markdown("""
    <style>
    .reportview-container {
        background-color: #FAFAFA; /* Light gray background for better contrast */
        color: #333333; /* Dark text color for better readability */
    }
    .sidebar .sidebar-content {
        background-color: #FFFFFF; /* White sidebar background */
        color: #333333; /* Dark text color */
        border-right: 2px solid #E0E0E0; /* Light gray border */
    }
    .stButton>button {
        background-color: #007BFF; /* Primary blue button background */
        color: #FFFFFF; /* White text color */
        border: none; /* Remove border */
        border-radius: 4px; /* Rounded corners */
    }
    .stButton>button:hover {
        background-color: #0056b3; /* Darker blue background on hover */
        color: #FFFFFF; /* White text on hover */
    }
    .stTextInput>div>input {
        border: 2px solid #007BFF; /* Blue border for text input */
        border-radius: 4px; /* Rounded corners */
        padding: 8px; /* Padding inside text input */
    }
    .stTextInput>div>input:focus {
        border: 2px solid #0056b3; /* Darker blue border on focus */
    }
    </style>
""", unsafe_allow_html=True)

st.title("YouTube Video Finder with TF-IDF Search")
query = st.text_input("Enter a category or search query", placeholder="e.g., tech news, cooking, video games")
if st.button("Search"):
    category = get_category_from_query(query)
    if category:
        fetch_and_display_videos(category)
