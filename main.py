import streamlit as st
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors


SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# Must match exactly what you set in the Google Cloud Console → Authorized redirect URIs
REDIRECT_URI = "https://ytappapi.streamlit.app"


def get_flow():
    """
    Create the OAuth 2.0 flow object from the client config
    stored in Streamlit Secrets.
    """
    return google_auth_oauthlib.flow.Flow.from_client_config(
        st.secrets["client_secret"],
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )


def build_youtube_client(credentials):
    """
    Build the YouTube API client from the given credentials.
    """
    return googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials
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
    Requires 'youtube.force-ssl' scope and the user must have a channel.
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


def show_data_options(youtube):
    """
    After we have a YouTube client, present a menu of data to fetch.
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
                st.error("Invalid option.")
                return

            if response is not None:
                st.json(response)
            else:
                st.warning("No response returned. Possibly no data or private data.")

        except googleapiclient.errors.HttpError as e:
            st.error(f"HTTP error: {e}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")


def main():
    st.title("YouTube Activity Retriever")

    # 1) Check if we already have valid credentials in session_state
    if "credentials" in st.session_state:
        st.success("Already authenticated with YouTube!")
        youtube = build_youtube_client(st.session_state["credentials"])
        show_data_options(youtube)
        return

    # 2) If not authenticated, see if 'code' is in the URL
    query_params = st.query_params
    if "code" not in query_params:
        # Not authorized → generate auth URL
        flow = get_flow()
        auth_url, _ = flow.authorization_url(prompt="consent")
        st.markdown(f"[Authorize with Google]({auth_url})", unsafe_allow_html=True)
        st.info("Click the link above to authorize the app to access your YouTube data.")
    else:
        # Exchange code for credentials
        code = query_params["code"][0]
        flow = get_flow()

        try:
            flow.fetch_token(code=code)
            st.session_state["credentials"] = flow.credentials

            # IMPORTANT: remove the 'code' param so it's not reused on rerun
            st.experimental_set_query_params()

            st.success("Successfully authenticated!")
            youtube = build_youtube_client(st.session_state["credentials"])
            show_data_options(youtube)

        except Exception as e:
            st.error(f"Error fetching token: {e}")


if __name__ == "__main__":
    main()
