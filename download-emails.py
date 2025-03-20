#!/bin/env python3
import os
import csv
import json
import argparse  # Added for command-line argument parsing

from gmail import Gmail
from llm import query_deepseek_json

def save_email_and_create_folder(parent, email, details):
    """Creates a folder for the trip and saves the email inside it."""
    
    outbound_date = details.get("outbound_departure_date", None)
    inbound_date = details.get("inbound_departure_date", None)
    
    if not outbound_date and not inbound_date:
        print("Skipping: Missing flight dates.")
        return

    folder_name = os.path.join(parent, 
        f"{outbound_date} to {inbound_date}" if outbound_date and inbound_date else
        outbound_date or inbound_date
    )
    os.makedirs(folder_name, exist_ok=True)

    # Save email as text
    email_filename = os.path.join(folder_name, "flight_confirmation.txt")
    with open(email_filename, "w", encoding="utf-8") as f:
        f.write("Subject: %s\n" % email['subject'])
        f.write("From: %s\n" % email['sender'])
        f.write("Date: %s\n" % email['date'])
        f.write("\n")
        f.write(email['plain_body'] + '\n')
        f.write("\n")
        f.write(email['html_body'] + '\n')
    
    # Save extracted data as JSON
    json_filename = os.path.join(folder_name, "flight_confirmation.json")
    with open(json_filename, "w", encoding="utf-8") as f:
        f.write(json.dumps(details, indent=2))
    
    print(f"Saved email to {email_filename}")

def append_to_csv(details, parent, filename='trips.csv'):
    """Stores extracted flight details in a CSV file."""
    csv_filename = os.path.join(parent, filename)
    file_exists = os.path.exists(csv_filename)

    with open(csv_filename, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write headers if file doesn't exist
        if not file_exists:
            writer.writerow([
                "Booking Ref",
                "Outbound Flight No.",
                "Outbound Departure Airport", "Outbound Departure Date", "Outbound Departure Time", 
                "Outbound Arrival Airport", "Outbound Arrival Date", "Outbound Arrival Time",
                "Inbound Flight No.",
                "Inbound Departure Airport", "Inbound Departure Date", "Inbound Departure Time", 
                "Inbound Arrival Airport", "Inbound Arrival Date", "Inbound Arrival Time",
            ])

        writer.writerow([
            details.get("booking_reference", ""),
            details.get("outbound_flight_number", ""),
            details.get("outbound_departure_airport", ""), details.get("outbound_departure_date", ""), details.get("outbound_departure_time", ""),
            details.get("outbound_arrival_airport", ""), details.get("outbound_arrival_date", ""), details.get("outbound_arrival_time", ""),
            details.get("inbound_flight_number", ""),
            details.get("inbound_departure_airport", ""), details.get("inbound_departure_date", ""), details.get("inbound_departure_time", ""),
            details.get("inbound_arrival_airport", ""), details.get("inbound_arrival_date", ""), details.get("inbound_arrival_time", ""),
        ])

    print(f"Added to CSV: {details.get('booking_reference', 'N/A')}")

def process_flight_emails(parent_directory, query):
    """Searches flight emails, extracts details, and saves them."""
    
    gmail = Gmail()
    
    messages = list(gmail.search_emails(query))
    print("Found", len(messages), "emails")

    all_flights = []
    for msg in messages:
        email_data = gmail.get_email(msg['id'])
        email = gmail.extract_email_content(email_data)

        prompt = '''
        You are a professional data extraction tool. Your task is to carefully analyse the provided <email> and extract the
        requested information as reported into the <response> tag. You must return a valid JSON data structure.
        <email>
        %s
        </email>
        <response>
        {
        "booking_reference": "ABCD",
        "outbound_flight_number": "AB1234",
        "outbound_departure_date": "2025-01-11",
        "outbound_departure_time": "10:30",
        "outbound_departure_airport": "London-Gatwick",
        "outbound_arrival_date": "2025-01-11",
        "outbound_arrival_time": "11:40",
        "outbound_arrival_airport": "Oslo-Gardermoen",
        "inbound_flight_number": "AB4321",
        "inbound_departure_date": "2025-02-22",
        "inbound_departure_time": "12:30",
        "inbound_departure_airport": "Oslo-Gardermoen",
        "inbound_arrival_date": "2025-02-22",
        "inbound_arrival_time": "13:45",
        "inbound_arrival_airport": "London-Gatwick"
        }
        </response>        
        ''' % email['html_body']

        print("%02d." % (len(all_flights) + 1), "Extracting data from", email['subject'], "sent", email['date'])
        result = query_deepseek_json(prompt)
        # print(json.dumps(result, indent=2))
        
        all_flights.append(result)
        save_email_and_create_folder(parent_directory, email, result)
        append_to_csv(result, parent_directory)
        print()
    
    print("Done")
   
def main():
    """Main function to process flight emails."""
    parser = argparse.ArgumentParser(description="Process flight emails and save details.")
    parser.add_argument(
        '--parent-directory', 
        type=str, 
        default='trips', 
        help="Parent directory to save extracted flight details (default: 'trips')"
    )
    parser.add_argument(
        '--query-file', 
        type=str, 
        default='email-query.txt', 
        help="File containing the email query (default: 'email-query.txt')"
    )
    args = parser.parse_args()

    parent_directory = args.parent_directory
    query_file = args.query_file

    # Load email query from file
    if not os.path.exists(query_file):
        raise FileNotFoundError(f"Query file '{query_file}' not found in the current directory.")
    
    with open(query_file, 'r', encoding='utf-8') as f:
        email_query = f.read().strip()

    process_flight_emails(parent_directory, email_query)

if __name__ == '__main__':
    main()


