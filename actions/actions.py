from robocorp.actions import action
from faker import Faker
import random
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from markdown import markdown

fake = Faker()

@action
def create_bulletin(title: str, content: str) -> str:
    """
    Creates a legal bulletin file using the content and the predetermined template and returns a link to the doc.
    
    Args:
        title (str): Title of the legal bulleting file. Should always include a unique identifier of the bulletin.
        content (str): Content of the legal bulletin to be placed in the template.
        
    Returns:
        str: link to the newly created document file in Google Drive
    """
    SERVICE_ACCOUNT_FILE = 'google_creds.json'
    SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/documents']

    try:
        credentials = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            # Create a service for the Drive API and Docs API
        drive_service = build('drive', 'v3', credentials=credentials)
        docs_service = build('docs', 'v1', credentials=credentials)
    except Exception as e:
        return f"Error authenticating with Google: {e}"

    # Create a Google Docs file
    file_metadata = {'name': title, 'mimeType': 'application/vnd.google-apps.document'}
    doc = drive_service.files().create(body=file_metadata, fields='id, webViewLink').execute()
    document_id = doc.get('id')

    # Simple text insertion
    requests = [{
        'insertText': {
            'location': {
                'index': 1,  # Index 1 is the beginning of the document
            },
            'text': content
        }
    }]

    # Execute the batchUpdate to add text
    result = docs_service.documents().batchUpdate(
        documentId=document_id,
        body={'requests': requests}
    ).execute()

    # Set permissions for anyone with the link to read and edit
    permission = {
        'type': 'anyone',
        'role': 'writer'
    }
    drive_service.permissions().create(
        fileId=doc.get('id'),
        body=permission,
        fields='id'
    ).execute()

    print(f"Created Google Doc with ID: {doc.get('id')}")
    print(f"Link to document: {doc.get('webViewLink')}")

    return f"Link to the created legal bulletin: {doc.get('webViewLink')}"

@action
def search_crm(term: str) -> str:
    """
    Searches CRM system for hits on companies, deals and contacts on a specific term

    Args:
        term (str): Search term to be used. Example: "International Semiconductor Ltd."

    Returns:
        str: List of entities found in the CRM for the search term
    """

    options = [0, 1, 2, 3]
    probabilities = [0.5, 0.1667, 0.1667, 0.1667]
    how_many = random.choices(options, weights=probabilities, k=1)[0]

    deals = ['yes', 'no']
    weights = [40, 60]  # 70% chance for 'yes', 30% chance for 'no'
    if how_many == 0:
        return "No matches found"
    else: 
        response = f"For term <{term}> following matches were found:\n"

        for i in range(how_many):

            # Use random.choices() to make a weighted random choice
            has_deals = random.choices(deals, weights=weights, k=1)[0]

            if has_deals == "yes":
                deal_text = f"There is {fake.pricetag()} invoices attributed to this contact in the past 5 years."
            else:
                deal_text = "There are no deals attributed to this contact."

            response += f"{fake.name()} is a contact in country unit {fake.country()}. Last contact {fake.date_between(start_date='-5y', end_date='today')}. {deal_text}\n"   

        print(response)
        return response
