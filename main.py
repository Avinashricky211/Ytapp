import streamlit as st
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

# Define constants
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# Update this to match your authorized redirect URI in the Google Cloud Console
REDIRECT_URI = "https://ytappapi.streamlit.app"

def get_flow():
    """
    Create the OAuth 2.0 flow object from the client config
    stored in Streamlit Secrets.
    """
    return google_auth_oauthlib.flow.Flow.from_client_config(
        st.secrets["client_secret"],  # This contains {"web": {...}}
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

def main():
    st.title("YouTube Activity Retriever")

    # Check for OAuth 2.0 authorization code in query params
    query_params = st.experimental_get_query_params()

    if "code" not in query_params:
        # No 'code' present → generate the authorization URL
        flow = get_flow()
        auth_url, _ = flow.authorization_url(prompt="consent")
        st.markdown(f"[Authorize with Google]({auth_url})", unsafe_allow_html=True)
        st.info("Click the link above to authorize the app to access your YouTube activity.")
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

        # Build the YouTube API client
        try:
            youtube = googleapiclient.discovery.build(
                API_SERVICE_NAME, API_VERSION, credentials=credentials
            )
        except Exception as e:
            st.error(f"Error building YouTube client: {e}")
            return

        st.success("Successfully authenticated!")
        st.write("Fetching your recent YouTube activities...")

        # Retrieve recent YouTube activities
        try:
            request = youtube.activities().list(
                part="snippet,contentDetails",
                mine=True,
                maxResults=10
            )
            response = request.execute()
            st.json(response)
        except googleapiclient.errors.HttpError as e:
            st.error(f"An error occurred while fetching activities: {e}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
