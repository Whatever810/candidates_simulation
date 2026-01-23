import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import date

players_to_scrape = {
    "Fabiano Caruana": "2020009",
    "Hikaru Nakamura": "2016192",
    "R Praggnanandhaa": "25059530",
    "Anish Giri": "24116068",
    "Wei Yi": "8603405",
    "Javokhir Sindarov": "14205483",
    "Andrey Esipenko": "24175439",
    "Matthias Bluebaum": "24651516"
}


def scrape_player_ratings(players_dict):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    results = []

    for name, fide_id in players_dict.items():
        url = f"https://ratings.fide.com/profile/{fide_id}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            ratings = {"Classical": None, "Rapid": None, "Blitz": None}
            
            def get_rating_from_class(class_name):
                div = soup.find('div', class_=class_name)
                if div:
                    p_tag = div.find('p')
                    if p_tag:
                        text = p_tag.get_text(strip=True)
                        if text.isdigit():
                            return int(text)
                return None

            ratings["Classical"] = get_rating_from_class("profile-standart profile-game")
            
            ratings["Rapid"] = get_rating_from_class("profile-rapid profile-game")
            
            ratings["Blitz"] = get_rating_from_class("profile-blitz profile-game")

            print(f"Found {name}: {ratings}")
            
            results.append({
                "Name": name,
                "FideID": fide_id,
                "Ratings": ratings
            })

            time.sleep(1)

        except Exception as e:
            print(f"Error scraping {name} ({fide_id}): {e}")

    return results

def save_to_json(data):
    today_str = date.today().strftime("%Y-%m-%d")
    filename = f"current_player_ratings_{today_str}.json"
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)
    
    print("-" * 50)
    print(f"All data saved to: {filename}")
    return filename

if __name__ == "__main__":
    data = scrape_player_ratings(players_to_scrape)
    save_to_json(data)
