Flight and photo download script

# Email query

Store in email-query.txt by default

```
(OSL OR Oslo) 
after:2012/01/01 (
    (from:norwegian.com AND subject:"travel documents") OR 
    (from:flysas.com AND subject:"your flight") OR 
    (from:ba.com AND subject:"e-ticket receipt")
)
```

# Config files

- credentials.json: downloaded from Google API console
- deepseek.json: `{"apiKey": "<key>"}`

# Gmail API setup

To access your Gmail inbox programmatically, you'll need to use the Gmail API. Here's how to set it up:

Step 1: Enable the Gmail API
Go to the Google Cloud Console.
Create a new project (or select an existing one).
Navigate to APIs & Services > Library.
Search for Gmail API and enable it.
Step 2: Set Up OAuth Credentials
Go to APIs & Services > Credentials.
Click Create Credentials and select OAuth 2.0 Client ID.
Configure the consent screen:
Select External if you're the only user (you can restrict access to your email).
Provide an app name and your email.
Under Scopes, add https://www.googleapis.com/auth/gmail.readonly.
Create OAuth credentials:
Select Desktop App or Web Application.
Download the generated credentials.json file.
