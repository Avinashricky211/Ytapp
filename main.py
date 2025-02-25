import streamlit as st
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

# --------------------------------------------------------------------------------
# SCOPES: using force-ssl for additional access (e.g., comments)
# --------------------------------------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# This must match exactly what is set in Google Cloud Console's Authorized redirect URIs
REDIRECT_URI = "https://ytappapi.streamlit.app"


def get_flow():
    """
    Create and return an OAuth 2.0 flow object using credentials from Streamlit Secrets.
    """
    return google_auth_oauthlib.flow.Flow.from_client_config(
        st.secrets["client_secret"],
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )


def build_youtube_client(credentials):
    """
    Build the YouTube API client using the provided credentials.
    """
    return googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials
    )


def fetch_liked_videos(youtube):
    """
    Fetch the user's liked videos (if public).
    """
    request = youtube.videos().list(
        part="snippet,contentDetails",
        myRating="like",
        maxResults=10
    )
    return request.execute()


def fetch_subscriptions(youtube):
    """
    Fetch the user's subscriptions (if public).
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
    Fetch comment threads from the user's channel.
    Requires 'youtube.force-ssl' scope and that the account has a channel.
    """
    # First, retrieve the user's channel ID
    channels_response = youtube.channels().list(
        part="id",
        mine=True
    ).execute()

    items = channels_response.get("items", [])
    if not items:
        st.warning("No channel found for this account.")
        return None

    channel_id = items[0]["id"]

    # Now fetch comment threads for that channel
    request = youtube.commentThreads().list(
        part="snippet",
        allThreadsRelatedToChannelId=channel_id,
        maxResults=10
    )
    return request.execute()


def show_data_options(youtube):
    """
    Show a selection of data types to fetch from YouTube.
    """
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
                st.warning("No data returned. Possibly the data is private or unavailable.")
        except googleapiclient.errors.HttpError as e:
            st.error(f"HTTP error: {e}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")


def main():
    st.title("YouTube Activity Retriever")

    # If credentials exist in session_state, we are already authenticated
    if "credentials" in st.session_state:
        st.success("Already authenticated with YouTube!")
        youtube = build_youtube_client(st.session_state["credentials"])
        show_data_options(youtube)
        return

    # Check for OAuth code in the URL query parameters
    query_params = st.experimental_get_query_params()
    if "code" not in query_params:
        # No code: prompt user to authenticate
        flow = get_flow()
        auth_url, _ = flow.authorization_url(prompt="consent")
        st.markdown(f"[Authorize with Google]({auth_url})", unsafe_allow_html=True)
        st.info("Click the link above to authorize the app to access your YouTube data.")
    else:
        # Code exists: attempt to exchange it for tokens
        code = query_params["code"][0]
        flow = get_flow()
        try:
            flow.fetch_token(code=code)
            st.session_state["credentials"] = flow.credentials  # Save tokens for later use

            # Clear the code from the URL to prevent reuse on reruns
            st.experimental_set_query_params()

            st.success("Successfully authenticated!")
            youtube = build_youtube_client(st.session_state["credentials"])
            show_data_options(youtube)
        except Exception as e:
            st.error(f"Error fetching token: {e}")


if __name__ == "__main__":
    main()
