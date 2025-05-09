from typing import List, Dict, Optional
from models import Event
from base_scraper import BaseScraper
import re


class ILoveQatarScraper(BaseScraper):
    def __init__(self, pages: int = 1):
        super().__init__("ILoveQatar")
        self.base_url = "https://www.iloveqatar.net/events/p{page_num}"
        self.pages = pages

    def scrape_events(self) -> List[Event]:
        all_events = []
        for page in range(1, self.pages + 1):
            print(f"Scraping page {page}...")
            url = self.base_url.format(page_num=page)
            try:
                response = self.make_request(url)
                soup = self.parse_html(response.content)
                event_links = [
                    a["href"]
                    for a in soup.find_all("a", class_="article-block__title")
                    if a.has_attr("href")
                ]

                for link in event_links:
                    try:
                        event_data = self.scrape_event_page(link)
                        if event_data:
                            event = self.transform_event(event_data)
                            all_events.append(event)
                    except Exception as e:
                        print(f"Error scraping event {link}: {e}")
            except Exception as e:
                print(f"Error scraping page {page}: {e}")

        return all_events

    def scrape_event_page(self, url: str) -> Optional[Dict]:
        try:
            response = self.make_request(url)
            soup = self.parse_html(response.content)

            category = "general"
            url_parts = url.split("/")
            if len(url_parts) > 5 and url_parts[4] == "events":
                category = url_parts[5].lower()

            # Extract title
            title = (
                soup.find("h1").get_text(strip=True) if soup.find("h1") else "No title"
            )

            # Extract date and time
            date_item = soup.find("div", class_="events-page-info__item _date")
            date = (
                self.clean_text(date_item.get_text(strip=True), prefix="Date:")
                if date_item
                else "No date"
            )

            time_item = soup.find("div", class_="events-page-info__item _time")
            time = (
                self.clean_text(time_item.get_text(strip=True), prefix="Time:")
                if time_item
                else "No time"
            )

            # Parse date and time into start/end
            start_date, end_date, start_time, end_time = self.parse_date_time(
                date, time
            )

            # Extract location
            location_item = soup.find("div", class_="events-page-info__item _location")
            location = (
                self.clean_text(location_item.get_text(strip=True), prefix="Location:")
                if location_item
                else "No location"
            )

            # Extract tickets and prices
            tickets_items = soup.find_all(
                "div", class_="events-page-info__item _tickets"
            )
            tickets = (
                self.clean_text(
                    tickets_items[0].get_text(strip=True), prefix="Tickets:"
                )
                if tickets_items
                else "No tickets"
            )
            prices = (
                self.clean_text(tickets_items[1].get_text(strip=True), prefix="Prices:")
                if len(tickets_items) > 1
                else "No prices"
            )

            # Extract description
            description_div = soup.find("div", {"class": "events-page-info"})
            # Find all p tags within this div
            paragraphs = description_div.find_all("p")
            # Combine all paragraphs into one string with proper spacing
            description = "\n\n".join(p.get_text(strip=True) for p in paragraphs)

            return {
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "start_time": start_time,
                "end_time": end_time,
                "time": time,  # Original time string
                "location": location,
                "tickets": tickets,
                "prices": prices,
                "description": description,
                "category": category,
                "link": url,
                "raw_data": {  # Store raw selectors for debugging
                    "date": str(date_item),
                    "time": str(time_item),
                    "location": str(location_item),
                },
            }
        except Exception as e:
            print(f"Error scraping event page {url}: {e}")
            return None

    def clean_text(self, text: str, prefix: str = None) -> str:
        """Remove prefix and any extra whitespace from text"""
        if prefix and text.startswith(prefix):
            text = text[len(prefix) :].strip()
        return text.strip()

    def parse_date_time(self, date_str: str, time_str: str) -> tuple:
        """Parse date and time strings into start/end components

        Args:
            date_str: Date string (e.g., "4 May 2025\n- 7 May 2025")
            time_str: Time string (e.g., "08:30 am\n- 04:00 pm")

        Returns:
            tuple: (start_date, end_date, start_time, end_time)
        """
        # Clean the strings first - remove extra whitespace, newlines
        date_str = self.clean_text(date_str)
        time_str = self.clean_text(time_str)

        # Default values
        start_date = end_date = date_str
        start_time = end_time = time_str

        # Handle date range - multiple formats:
        # 1. "4 May 2025 - 7 May 2025"
        # 2. "4 May 2025\n- 7 May 2025"
        # 3. "28 May 2025\n- 29 May 2025"

        # First try splitting on hyphen with optional whitespace/newlines
        date_parts = re.split(r"\s*-\s*", date_str)
        if len(date_parts) == 2:
            start_date = date_parts[0].strip()
            end_date = date_parts[1].strip()
        else:
            # Alternative format: "25 - 26 December 2023"
            date_range_match = re.match(r"(\d+)\s*-\s*(\d+)\s*(.*)", date_str)
            if date_range_match:
                day1, day2, month_year = date_range_match.groups()
                start_date = f"{day1} {month_year}"
                end_date = f"{day2} {month_year}"

        # Handle time range - similar approach
        time_parts = re.split(r"\s*-\s*", time_str)
        if len(time_parts) == 2:
            start_time = time_parts[0].strip()
            end_time = time_parts[1].strip()
        else:
            # Alternative time format handling if needed
            time_range_match = re.match(r"(.+)\s*-\s*(.+)", time_str)
            if time_range_match:
                start_time, end_time = time_range_match.groups()

        return start_date, end_date, start_time, end_time

    def transform_event(self, raw_event: Dict) -> Event:
        """Transform raw event data into standardized Event object"""
        return Event(
            title=raw_event["title"],
            start_date=raw_event["start_date"],
            end_date=raw_event["end_date"],
            time=raw_event["time"],
            start_time=raw_event["start_time"],
            end_time=raw_event["end_time"],
            location=raw_event["location"],
            description=raw_event["description"],
            category=raw_event["category"],
            price=raw_event["prices"],
            tickets=raw_event["tickets"],
            link=raw_event["link"],
            source=self.source_name,
            raw_data=raw_event.get("raw_data"),
        )
