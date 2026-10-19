import streamlit as st
from googleapiclient.discovery import build
import pandas as pd

# --- UI Setup ---
st.set_page_config(page_title="Vanguard Nature Engine", layout="wide")
st.title("🦁 Vanguard Nature: Topic Engine")
st.markdown("Find high-opportunity documentary topics on YouTube.")

# --- Sidebar Controls ---
with st.sidebar:
    st.header("Search Settings")
    # Streamlit securely handles your API key via "Secrets" (explained in step 4)
    api_key = st.secrets["YOUTUBE_API_KEY"] 
    search_query = st.text_input("Enter Topic (e.g., Savannah predators)", "African savanna predators documentary")
    run_search = st.button("Run Search")

# --- Logic ---
if run_search:
    with st.spinner(f"Searching YouTube for '{search_query}'..."):
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Search for long-form videos
        search_request = youtube.search().list(
            q=search_query,
            part='snippet',
            type='video',
            videoDuration='long', 
            maxResults=30
        )
        search_response = search_request.execute()
        
        video_ids = []
        channel_ids = []
        video_titles = []
        
        for item in search_response.get('items', []):
            video_ids.append(item['id']['videoId'])
            channel_ids.append(item['snippet']['channelId'])
            video_titles.append(item['snippet']['title'])
            
        if not video_ids:
            st.error("No videos found. Try a different search query.")
        else:
            # Get Video Views and Channel Subscribers
            video_request = youtube.videos().list(part='statistics', id=','.join(video_ids))
            video_response = video_request.execute()
            
            unique_channel_ids = list(set(channel_ids))
            channel_request = youtube.channels().list(part='statistics,snippet', id=','.join(unique_channel_ids))
            channel_response = channel_request.execute()
            
            channel_data = {}
            for item in channel_response.get('items', []):
                channel_data[item['id']] = {
                    'subs': int(item['statistics'].get('subscriberCount', 0)), 
                    'name': item['snippet']['title']
                }
                
            results = []
            for i in range(len(video_ids)):
                try:
                    views = int(video_response['items'][i]['statistics'].get('viewCount', 0))
                except IndexError:
                    views = 0
                    
                subs = channel_data[channel_ids[i]]['subs']
                outlier_score = round(views / subs, 2) if subs > 0 else views
                    
                results.append({
                    'Title': video_titles[i],
                    'Channel': channel_data[channel_ids[i]]['name'],
                    'Score': outlier_score,
                    'Views': views,
                    'Subs': subs,
                    'URL': f"https://www.youtube.com/watch?v={video_ids[i]}"
                })
                
            # Display the data
            df = pd.DataFrame(results)
            df_sorted = df.sort_values(by='Score', ascending=False).reset_index(drop=True)
            
            st.success("Search Complete!")
            # This renders a mobile-friendly, sortable table
            st.dataframe(
                df_sorted, 
                column_config={"URL": st.column_config.LinkColumn("Watch Link")},
                use_container_width=True
            )
