from robocorp.tasks import task
from robocorp import vault, storage

from RPA.HTTP import HTTP
from RPA.PDF import PDF
# from RPA.Notifier import Notifier
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from bs4 import BeautifulSoup
from openai import OpenAI
from datetime import datetime
from dateutil.relativedelta import relativedelta
import requests
from datetime import datetime
import json
import re

ASSET_NAME = "bis-automation-last-run"

def _get_new_rules():
    """Goes to BIS site to check if there are new rules or notices, and if yes reads
    their documents and summarises them to Slack."""

    # Get the reference date from Asset Storage, when was it ran last.
    try:
        reference_time_text = storage.get_text(ASSET_NAME)
        reference_time = datetime.strptime(reference_time_text, '%Y-%m-%d')
    except:
        print("can not get last run date, make it up")
        today = datetime.today()
        reference_time = today - relativedelta(months=2)

    # Store the new run reference date to the Asset Storage
    try:
        date_string = datetime.today().strftime('%Y-%m-%d')
        status = storage.set_text(ASSET_NAME, date_string)
    except:
        print(f"Error in storing last run date")

    # -----
    # DEBUG - SET THE TIME WHERE I WANT
    # -----
    reference_time = datetime.strptime("2024-04-10", '%Y-%m-%d')
    print(reference_time)

    # Robocorp and some basic things up
    http = HTTP()
    pdf = PDF()
    baseurl = "https://www.bis.doc.gov"

    # OpenAI things up, the API key comes from the Vault
    openai_secret = vault.get_secret("OpenAI")
    client = OpenAI(
        api_key=openai_secret["key"]
    )

    # Get a bs soup out of the site source
    response = requests.get("https://www.bis.doc.gov/index.php/federal-register-notices")
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all the 'p' elements with the text 'Publication Date:'
    publication_date_elements = []
    for p in soup.find_all('p'):
        if 'Publication Date:' in p.get_text():
            publication_date_elements.append(p)

    result_list = []
    for element in publication_date_elements:
        entire_text = element.get_text()
        # Some elements contain unicode chars, this should clean that up
        normalized_text = re.sub(r'\s+', ' ', entire_text)
        # Get the publication date of part of the element
        date_string = normalized_text.split(": ")[1]
        date_object = datetime.strptime(date_string, "%m/%d/%Y")

        # Find the next link (a) after the date element, that must be the doc link until they break the structure.    
        next_a_element = element.find_next('a')
        # Add the date and link to the result list
        result_list.append((date_object, next_a_element.get('href')))

    # Go through all the elements, and only get the links that are newer than reference date.
    links = [link for date, link in result_list if date >= reference_time]

    final_results = []

    for link in links:

        # Mate the base url with the rest of it, make up a filename and then download
        dl_url = baseurl+link
        filename = "files/" + dl_url.split('=')[-1] + ".pdf"
        http.download(dl_url, filename)

        # Get all the text from the PDF, and then loop page oy page to construct a string
        # to be used within the prompt to LLM
        text = pdf.get_text_from_pdf(filename)

        rule_string = ""
        for page_number, content in text.items():
            rule_string += f'Page {page_number}:'
            rule_string += content
            rule_string += '\n---\n'

        #print(f"-------------------------------------------------------\n{rule_string}")

        # Prompt to OpenAI. No fancy templates here, just all in at once.
        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an assistant for the enterprise legal team, helping them to understand the newly updated Federal Buereau of Industry and Security rules and notifications.",
                },
                {
                    "role": "user",
                    "content": "Your task is to summarize the new rule or notification by the BIS, and highlight the parts that might be most relevant for global enterprise operations. Try avoiding to include the boilerplate language in your summary, but to focus directly on the actual relevant content. Aim for a summary that can be consumed by a legal person in less than a minute. Never drop relevant entity names, or enforcement dates from your summary. Always start with a one liner of what the rule or notice is about and it's publication and enforcement dates, followed by an empty line. In cases the rule contains entity names, always list them all in the summary. Please observe that there might be fragments of other rules content in the attached snippet below. Only use the parts of the content from the first main title, which is indicated for example by a Docket number. Also in the end there might be fragments of the following rule, which are not relevant anymore.\n\nBIS RULE CONTENT:\n" + rule_string,
                }
            ],
            model="gpt-4-0125-preview",
        )

        final_results.append((filename, f"NEW BIS NOTIFICATION SUMMARY:\n\n{completion.choices[0].message.content}\n\nLink: {dl_url}"))

    return final_results

@task
def compliance_checker():
    """Goes to BIS site to check if there are new rules or notices, and if yes reads
    their documents and summarises them and creates an assistant thread our of them."""

    rules = _get_new_rules()

    print(rules)

    cookie = {"opengpts_user_id": "89759853-0479-450f-9524-26d68ed198da"}
    asst_id = "5c96c978-aae4-490a-809f-898f12ee3e99"
    base_url = "http://127.0.0.1:8100"

    for rule in rules:

        # Create a thread
        resp = requests.post(f'{base_url}/threads', cookies=cookie, json={
            "name": rule[0],
            "assistant_id": asst_id
        }).content

        thread_id = json.loads(resp.decode('utf-8'))["thread_id"]

        # Add file to the thread for rag
        files = {
            'files': (rule[0], open(rule[0], 'rb'), 'application/pdf')
        }

        config = {
            'config': json.dumps({
                'configurable': {
                    'thread_id': thread_id
                }
            })
        }

        response = requests.post(f'{base_url}/ingest', files=files, cookies=cookie, data=config, headers={'accept': 'application/json'})

        if response.status_code == 200:
            print("File upload successful!")
        else:
            print(f"Request failed with status code: {response.status_code}")
            print(response.text)

        # Add AI messages to prime the thread
        # requests.post(
        #    f'{base_url}/threads/{thread_id}/messages', 
        #    cookies=cookie, json={
        #        "messages": [{
        #            "content": rule[1],
        #            "type": "ai",
        #        },
        #        {
        #            "content": "Ask me anything you'd like to know more!",
        #            "type": "ai",
        #        }
        #        ]
        #    }
        #).content

        # Run the thread
        resp1 = requests.post(f'{base_url}/runs', cookies=cookie, json={
            "assistant_id": asst_id,
            "thread_id": thread_id,
            "input": [{
                    "content": rule[1],
                    "type": "ai",
                },
                ]
            }).content

        # Get thread content
        messages = requests.get(
            f'{base_url}/threads/{thread_id}/messages', 
            cookies=cookie
        ).content

        print(f"\n\nMESSAGES:\n{messages}n\n")

        # notif = Notifier()
        # slack_secrets = vault.get_secret("Slack")
        gmail_credentials = vault.get_secret("Google")

        # Email properties
        sent_from = gmail_credentials["email"]
        to = ["tommi@robocorp.com"]
        subject = f"LEGAL COMPLIANCE NEWS: New BIS Rule published: {rule[0]} "

        formatted_rule_text = rule[1].replace('\n\n', '<br><br>').replace('\n', '<br>')

        # HTML email content
        html = f"""\
        <html>
        <head></head>
        <body>
            <p>New BIS Rule published!<br>
            Act on it: <a href='http://localhost:5173/thread/{thread_id}'>http://localhost:5173/thread/{thread_id}</a><br>
            </p>
            <p>
            Summary:<br>
            {formatted_rule_text}
            </p>
        </body>
        </html>
        """

        # Create message container - the correct MIME type is multipart/alternative.
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sent_from
        msg['To'] = ", ".join(to)

        # Record the MIME types of both parts - text/plain and text/html.
        # part1 = MIMEText(text, 'plain')  # If you want to include plain text as well
        part2 = MIMEText(html, 'html')

        # Attach parts into message container. According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        # msg.attach(part1)  # Uncomment this line if you included plain text
        msg.attach(part2)

        try:
            # Create SMTP session for sending the email
            smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)  # Use 587 with smtplib.SMTP if your server prefers starttls
            smtp_server.ehlo()
            smtp_server.login(gmail_credentials["email"], gmail_credentials["email-app-password"])
            
            # Send the email
            smtp_server.sendmail(sent_from, to, msg.as_string())
            smtp_server.close()
            print("Email sent successfully!")
        except Exception as e:
            print("Failed to send email:", e)

        # notif.notify_gmail(f"New BIS Rule published! Act on it: <a href='http://localhost:5173/thread/{thread_id}'>http://localhost:5173/thread/{thread_id}</a>\n\nSummary:\n{rule[1]}", "tommi@robocorp.com", gmail_credentials["email"], gmail_credentials["email-app-password"])

        print(f"Your new thread is here: http://localhost:5173/thread/{thread_id}")

