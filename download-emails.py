import os
import re
import csv
import dateutil.parser
import json

import pandas as pd

from gmail import Gmail
from llm import query_deepseek_json

def extract_flight_details_regex(email_content):
    """
    Extract flight details from email content using NLP and pattern recognition
    
    Args:
        email_content: dict with 'subject', 'plain_body', and 'html_body'
    
    Returns:
        list: List of dictionaries containing flight details
    """
    # Combine subject and body for analysis
    text = email_content['subject'] + "\n"
    
    # Prefer plain text for parsing if available, otherwise use HTML with tags stripped
    if email_content['plain_body']:
        text += email_content['plain_body']
    elif email_content['html_body']:
        # Simple HTML tag removal (for more complex HTML, consider using BeautifulSoup)
        text += re.sub(r'<[^>]+>', ' ', email_content['html_body'])
    
    flights = []
     
    # Extract potential flight numbers
    flight_number_patterns = [
        r'\b[A-Z]{2}\s*\d{1,4}\b',  # AA 1234
        r'\b[A-Z]{2}\d{1,4}\b',      # AA1234
        r'\b[A-Z]{1,2}\s*\d{3,4}[A-Z]?\b'  # B 1234, DL 123B
    ]
    
    flight_numbers = []
    for pattern in flight_number_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            flight_num = match.group().replace(' ', '')
            if len(flight_num) >= 3:  # Avoid false positives
                flight_numbers.append({
                    'flight_number': flight_num,
                    'position': match.start()
                })
    
    # Extract dates
    dates = []
    # Find dates in common formats
    date_patterns = [
        r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',  # 01/01/2023
        r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}\b',  # 1 Jan 2023
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?\s*,?\s*\d{2,4}\b',  # Jan 1, 2023
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?\b'  # Jan 1st (current year implied)
    ]
    
    for pattern in date_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            date_str = match.group()
            try:
                parsed_date = dateutil.parser.parse(date_str, fuzzy=True)
                dates.append({
                    'date': parsed_date,
                    'original': date_str,
                    'position': match.start()
                })
            except:
                pass
    
    # Extract times
    times = []
    time_patterns = [
        r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b',  # 10:30 AM
        r'\b\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)\b',  # 10 AM, 10:30 AM
        r'\b\d{1,2}:\d{2}\b'  # 24-hour format: 14:30
    ]
    
    for pattern in time_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            time_str = match.group()
            try:
                # Parse as time only
                parsed_time = dateutil.parser.parse(time_str).time()
                times.append({
                    'time': parsed_time,
                    'original': time_str,
                    'position': match.start()
                })
            except:
                pass
    
    # Extract airport codes
    airport_codes = []
    airport_pattern = r'\b[A-Z]{3}\b'  # Three-letter IATA airport codes
    
    # Common words that might be confused with airport codes
    exclusions = {'THE', 'AND', 'FOR', 'NOT', 'BUT', 'YOU', 'ALL', 'ANY', 'GET', 'NOW', 'NEW'}
    
    matches = re.finditer(airport_pattern, text)
    for match in matches:
        code = match.group()
        if code not in exclusions:
            airport_codes.append({
                'code': code,
                'position': match.start()
            })
    
    # Extract booking references
    booking_refs = []
    booking_ref_patterns = [
        r'\b(?:confirmation|booking|reservation|reference)(?:\s+(?:code|number|#))?\s*[:;]?\s*([A-Z0-9]{5,8})\b',
        r'\b(?:PNR|Record Locator|Booking Reference)(?:\s+(?:code|number|#))?\s*[:;]?\s*([A-Z0-9]{5,8})\b',
        r'\b([A-Z0-9]{6})\b'  # Six character alphanumeric code is common for booking references
    ]
    
    for pattern in booking_ref_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) > 0:
                ref = match.group(1)
            else:
                ref = match.group()
            
            # Validate to reduce false positives
            if re.match(r'^[A-Z0-9]{5,8}$', ref):
                booking_refs.append({
                    'reference': ref,
                    'position': match.start()
                })
    
    # Associate data into flight records
    # This is a simplified approach - in reality, you'd need more sophisticated contextual analysis
    
    # Method 1: Look for flight numbers and associate nearby information
    for flight_num in flight_numbers:
        flight_record = {'flight_number': flight_num['flight_number']}
        pos = flight_num['position']
        
        # Find closest date before and after
        prev_date = None
        next_date = None
        min_prev_distance = float('inf')
        min_next_distance = float('inf')
        
        for date in dates:
            if date['position'] < pos and pos - date['position'] < min_prev_distance:
                min_prev_distance = pos - date['position']
                prev_date = date
            elif date['position'] > pos and date['position'] - pos < min_next_distance:
                min_next_distance = date['position'] - pos
                next_date = date
        
        # Similar approach for times, airports, etc.
        flight_record['departure_date'] = prev_date['date'] if prev_date else None
        flight_record['arrival_date'] = next_date['date'] if next_date else None
        
        # Find closest airports
        airports_found = []
        for airport in airport_codes:
            distance = abs(pos - airport['position'])
            if distance < 500:  # Arbitrary threshold
                airports_found.append((airport['code'], distance))
        
        # Sort by distance
        airports_found.sort(key=lambda x: x[1])
        
        # Assign origin and destination
        if len(airports_found) >= 2:
            if airports_found[0][1] < airports_found[1][1]:
                flight_record['origin'] = airports_found[0][0]
                flight_record['destination'] = airports_found[1][0]
            else:
                flight_record['origin'] = airports_found[1][0]
                flight_record['destination'] = airports_found[0][0]
        elif len(airports_found) == 1:
            flight_record['origin'] = airports_found[0][0]
            flight_record['destination'] = None
        
        # Add booking reference if found
        if booking_refs:
            flight_record['booking_reference'] = booking_refs[0]['reference']
        
        flights.append(flight_record)
    
    # Method 2: Look for contextual clues
    segments = text.split('\n')
    for i, segment in enumerate(segments):
        if re.search(r'\b(?:depart|departure|leave|from)\b', segment, re.IGNORECASE):
            # This segment might contain departure info
            dep_airports = [code['code'] for code in airport_codes 
                          if code['position'] >= text.find(segment) and 
                          code['position'] < text.find(segment) + len(segment)]
            
            if dep_airports and not any(flight.get('origin') == dep_airports[0] for flight in flights):
                # Create a new flight record or update existing
                flight_record = {'origin': dep_airports[0]}
                flights.append(flight_record)
    
    # Clean up and validate flights
    valid_flights = []
    for flight in flights:
        if 'flight_number' in flight or ('origin' in flight and 'destination' in flight):
            valid_flights.append(flight)
    
    return valid_flights

def save_email_and_create_folder(parent, email, details):
    """Creates a folder for the trip and saves the email inside it."""
    
    outbound_date = details.get("outbound_departure_date", None)
    inbound_date = details.get("inbound_departure_date", None)
    
    if not outbound_date or not inbound_date:
        print("Skipping: Missing flight dates.")
        return

    folder_name = os.path.join(parent, f"{outbound_date} to {inbound_date}")
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

def append_to_csv(details):
    """Stores extracted flight details in a CSV file."""
    csv_filename = "flights.csv"
    file_exists = os.path.exists(csv_filename)

    with open(csv_filename, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write headers if file doesn't exist
        if not file_exists:
            writer.writerow(["Booking Ref", "Outbound Date", "Outbound Time", "Flight No.", "Dep Airport", "Arr Airport",
                             "Inbound Date", "Inbound Time", "Flight No.", "Dep Airport", "Arr Airport"])

        writer.writerow([
            details["booking_ref"],
            details["outbound"]["date"], details["outbound"]["time"], details["outbound"]["flight_no"],
            details["outbound"]["dep_airport"], details["outbound"]["arr_airport"],
            details["inbound"]["date"], details["inbound"]["time"], details["inbound"]["flight_no"],
            details["inbound"]["dep_airport"], details["inbound"]["arr_airport"]
        ])

    print(f"Added to CSV: {details['booking_ref']}")

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

        print("Extracting data from", email['subject'], "sent", email['date'])
        result = query_deepseek_json(prompt)
        print(json.dumps(result, indent=2))
        
        all_flights.append(result)
        save_email_and_create_folder(parent_directory, email, result)

        break
    
    print("Done")
   
if __name__ == '__main__':
    process_flight_emails('trips', '''\
        (OSL OR Oslo) 
        after:2012/01/01 (
            (from:norwegian.com AND subject:"travel documents") OR 
            (from:flysas.com AND subject:"your flight") OR 
            (from:ba.com AND subject:"e-ticket receipt")
        )'''
    )


