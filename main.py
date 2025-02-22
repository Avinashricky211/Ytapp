import streamlit as st
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors


SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# Your Streamlit app URL, must match an authorized redirect URI in Google Cloud Console
REDIRECT_URI = "https://ytappapi.streamlit.app"

def get_flow():
    """
    Create OAuth 2.0 flow object from the client config
    stored in Streamlit Secrets.
    """
    return google_auth_oauthlib.flow.Flow.from_client_config(
        st.secrets["client_secret"], 
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

def fetch_liked_videos(youtube):
    """
    Fetch the user's liked videos (if likes are public).
    """
    request = youtube.videos().list(
        part="snippet,contentDetails",
        myRating="like",
        maxResults=10
    )
    return request.execute()

def fetch_subscriptions(youtube):
    """
    Fetch the user's subscriptions (if subscriptions are public).
    """
    request = youtube.subscriptions().list(
        part="snippet,contentDetails",
        mine=True,
        maxResults=10
    )
    return request.execute()

def fetch_playlists(youtube):
    """
    Fetch the user's playlists.
    """
    request = youtube.playlists().list(
        part="snippet,contentDetails",
        mine=True,
        maxResults=10
    )
    return request.execute()

def fetch_channel_comments(youtube):
    """
    Fetch comment threads on the user's channel.
    Requires 'youtube.force-ssl' scope in most cases.
    """
    # Get the user's channel ID
    channels_response = youtube.channels().list(
        part="id",
        mine=True
    ).execute()
    
    items = channels_response.get("items", [])
    if not items:
        st.warning("No channel found for this account.")
        return None
    
    channel_id = items[0]["id"]
    
    # Fetch comment threads for that channel
    request = youtube.commentThreads().list(
        part="snippet",
        allThreadsRelatedToChannelId=channel_id,
        maxResults=10
    )
    return request.execute()

def main():
    st.title("YouTube Activity Retriever")

    # Check for OAuth code in the query params
    query_params = st.query_params

    if "code" not in query_params:
        # Not yet authorized → generate the auth URL
        flow = get_flow()
        auth_url, _ = flow.authorization_url(prompt="consent")
        st.markdown(f"[Authorize with Google]({auth_url})", unsafe_allow_html=True)
        st.info("Click the link above to authorize the app to access your YouTube data.")
        return
    else:
        # We have an authorization code → exchange it for credentials
        code = query_params["code"][0]
        flow = get_flow()
        try:
            flow.fetch_token(code=code)
        except Exception as e:
            st.error(f"Error fetching token: {e}")
            return

        credentials = flow.credentials
        st.success("Successfully authenticated!")

        # Build the YouTube API client
        try:
            youtube = googleapiclient.discovery.build(
                API_SERVICE_NAME, API_VERSION, credentials=credentials
            )
        except Exception as e:
            st.error(f"Error building YouTube client: {e}")
            return

        st.write("**Select the type of YouTube data to retrieve:**")
        option = st.radio(
            label="Data type",
            options=["Liked Videos", "Comments", "Shares (Placeholder)", "Playlists", "Subscriptions"]
        )

        if st.button("Fetch Data"):
            try:
                if option == "Liked Videos":
                    response = fetch_liked_videos(youtube)
                elif option == "Comments":
                    response = fetch_channel_comments(youtube)
                elif option == "Shares (Placeholder)":
                    st.warning("YouTube API does not provide direct 'Shares' data.")
                    return
                elif option == "Playlists":
                    response = fetch_playlists(youtube)
                elif option == "Subscriptions":
                    response = fetch_subscriptions(youtube)
                else:
                    st.error("Invalid option selected.")
                    return

                if response is not None:
                    st.json(response)
                else:
                    st.warning("No response returned. Possibly no data or private data.")
            except googleapiclient.errors.HttpError as e:
                st.error(f"HTTP error fetching data: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
