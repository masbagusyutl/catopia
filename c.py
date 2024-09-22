import requests
import random
import json
import time
from datetime import datetime, timedelta
from colorama import Fore, Style, init
import os

init(autoreset=True)  # Initialize colorama for cross-platform colored text

# Function to convert ISO 8601 timestamp or another format to datetime
def parse_datetime(timestamp):
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(timestamp, '%a, %d %b %Y %H:%M:%S GMT')
        except ValueError:
            raise ValueError(f"Unrecognized datetime format: {timestamp}")

def is_time_to_harvest(planted_at, duration, remaining_seconds=None):
    if remaining_seconds is None:
        planted_time = parse_datetime(planted_at)
        harvest_time = planted_time + timedelta(seconds=duration)
        return datetime.now() >= harvest_time
    else:
        return remaining_seconds <= 0

def convert_timestamp_to_readable(timestamp):
    dt = parse_datetime(timestamp)
    return dt.strftime("%d %B %Y, %H:%M:%S")

def login(init_data):
    url = "https://api.catopia.io/api/v1/auth/telegram"
    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,id;q=0.8,su;q=0.7",
        "authorization": "Bearer",
        "cache-control": "no-cache",
        "content-type": "application/json; charset=UTF-8",
        "pragma": "no-cache",
        "sec-ch-ua": "\"Not)A;Brand\";v=\"99\", \"Google Chrome\";v=\"127\", \"Chromium\";v=\"127\"",
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": "\"Android\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "Referer": "https://build.catopia.io/",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }

    body = {
        "initData": init_data
    }

    response = requests.post(url, json=body, headers=headers)

    # Check if response content is valid JSON
    try:
        data = response.json()  # Attempt to parse JSON
    except json.JSONDecodeError:
        print(f"Error: Response could not be decoded as JSON. Response text: {response.text}")
        return None, None

    # Ensure the data is a dictionary before accessing its keys
    if isinstance(data, dict):
        # Check if the 'success' key exists and is true
        if data.get('success'):
            access_token = data['data'].get('accessToken')
            refresh_token = data['data'].get('refreshToken')
            return access_token, refresh_token
        else:
            print(f"Login failed: {data}")
    else:
        print(f"Unexpected response format: {data}")

    return None, None

def create_headers(access_token):
    return {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,id;q=0.8,su;q=0.7",
        "authorization": f"Bearer {access_token}",
        "cache-control": "no-cache",
        "content-type": "application/json; charset=UTF-8",
        "pragma": "no-cache",
        "sec-ch-ua": "\"Not)A;Brand\";v=\"99\", \"Google Chrome\";v=\"127\", \"Chromium\";v=\"127\"",
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": "\"Android\"",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "Referer": "https://build.catopia.io/",
        "Referrer-Policy": "strict-origin-when-cross-origin"
    }

def get_user_info(access_token):
    url = "https://api.catopia.io/api/v1/user/me?limit=3000"
    headers = create_headers(access_token)
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json().get('data', {})
        full_name = data.get('fullName')
        level = data.get('level')
        return full_name, level
    else:
        response.raise_for_status()

def collect(access_token):
    url = "https://api.catopia.io/api/v1/user-collection?limit=3000"
    headers = create_headers(access_token)
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json().get('data', {})
        golden_coin = data.get('goldenCoin')
        gem = data.get('gem')
        boost_settings = data.get('boostSettings', {})
        return golden_coin, gem, boost_settings
    else:
        response.raise_for_status()

def land(access_token):
    url = "https://api.catopia.io/api/v1/players/land?limit=3000"
    headers = create_headers(access_token)
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json().get('data', {})
        empty_land = data.get('emptyLand', [])
        occupied_land = data.get('occupiedLand', [])
        
        print(Fore.WHITE + f"\n=============== Lahan Kosong ===============")
        if empty_land:
            sorted_empty_land = sorted(empty_land, key=lambda x: x['slotId'])
            for item in sorted_empty_land:
                slot_id = item.get('slotId', 'N/A')
                planted_at = item.get('plantedAt', 'N/A')
                planted_at_display = "🌱 Belum Ditanam" if planted_at is None else f"🕒 {planted_at}"
                print(Fore.WHITE + f"Slot ID: {slot_id} | Status: {planted_at_display}")
        else:
            print(Fore.RED + f"Tidak ada data lahan kosong.")
        
        print(Fore.WHITE + f"\n=============== Lahan Nanam ===============")
        if occupied_land:
            sorted_occupied_land = sorted(occupied_land, key=lambda x: x['slotId'])
            for item in sorted_occupied_land:
                id = item.get('id', 'N/A')
                slot_id = item.get('slotId', 'N/A')
                planted_at = item.get('plantedAt', 'N/A')
                planted_name = item.get('plantName', 'N/A')
                planted_id = item.get('plantId', 'N/A')
                duration = item.get('duration')
                planted_at_display = f"🕒 {planted_at}" if planted_at is not None else "🌱 Belum Ditanam"
                print(Fore.WHITE + f"Slot ID: {slot_id} | Nama : {planted_name} | Status: {planted_at_display} | Duration: {duration} seconds")
        else:
            print(Fore.RED + f"Tidak ada data lahan nanam.\n")
        
        return empty_land, occupied_land
    else:
        response.raise_for_status()

def nanam_with_retry(access_token, plant_id, land_id, max_retries=1, delay=2):
    for attempt in range(max_retries):
        response_data = nanam(access_token, plant_id, land_id)
        if response_data and response_data.get('statusCode') == 201:
            print(Fore.GREEN + f"Penanaman pada lahan {land_id} berhasil pada percobaan ke-{attempt + 1}.")
            return response_data
        else:
            print(Fore.RED + f"Penanaman pada lahan {land_id} gagal pada percobaan ke-{attempt + 1}. Mencoba lagi dalam {delay} detik...")
            time.sleep(delay)
    print(Fore.RED + f"Gagal menanam pada lahan {land_id} setelah {max_retries} percobaan.")
    return None

def nanam(access_token, plant_id, land_id):
    url = "https://api.catopia.io/api/v1/players/plant"
    headers = create_headers(access_token)
    body = {
        "plantId": plant_id,
        "landId": land_id
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(body))
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(Fore.RED + f"HTTP error occurred: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Error during request: {e}")
        return None
    
    try:
        return response.json()
    except json.JSONDecodeError:
        print("Failed to decode JSON from response.")
        return None

def panen(access_token, planted_id, land_id):
    url = "https://api.catopia.io/api/v1/players/plant/harvest"
    headers = create_headers(access_token)
    body = {
        "plantId": planted_id,
        "landId": land_id
    }
    
    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(Fore.RED + f"HTTP error occurred: {e}")
        return {"statusCode": response.status_code, "message": str(e)}
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Error during request: {e}")
        return {"statusCode": 500, "message": "Request failed"}

def plant(access_token):
    url = "https://api.catopia.io/api/v1/players/plant?limit=3000"
    headers = create_headers(access_token)
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('data', [])
    else:
        response.raise_for_status()

def buy_plant(access_token, num_seeds, gem):
    num_seeds *= 2  # Menggandakan jumlah bibit yang dibeli
    
    choices = display_choices()
    selected_plants = []
    
    for _ in range(num_seeds):
        # Filter out "Potato" and "Rose" if the Gem balance is less than 2000
        if gem < 2000:
            print(Fore.YELLOW + "Gem kurang dari 2000, tidak bisa membeli Potato 🥔 atau Rose 🌹.")
        
        valid_choices = {k: v for k, v in choices.items() if not (v[0] in ["Potato 🥔", "Rose 🌹"] and gem < 2000)}
        
        # Randomly select from the valid choices
        selection = random.choice(list(valid_choices.keys()))
        plant, store_id, price_per_unit = valid_choices[selection]
        
        print(Fore.WHITE + f"Memilih bibit tanaman: {plant}")
        
        unit = 2 if plant in ["Potato 🥔", "Rose 🌹"] else 1
        total_price = price_per_unit * unit
        print(Fore.WHITE + f"Harga total untuk {unit} biji {plant} adalah {total_price}.")
        
        confirmation = 'y'
        if confirmation == 'y':
            url = "https://api.catopia.io/api/v1/store/buy"
            headers = create_headers(access_token)
            body = {
                "storeId": store_id,
                "price": total_price,
                "unit": unit
            }
            
            response = requests.post(url, headers=headers, data=json.dumps(body))
            
            if response.status_code == 201:
                print(Fore.GREEN + f"Pembelian bibit tanaman '{plant}' sukses")
                
                plant_info = {
                    'id': store_id,
                    'name': plant,
                    'harvestYieldGold': price_per_unit,
                    'duration': 7200  # Contoh durasi, sesuaikan dengan data sebenarnya
                }
                selected_plants.append(plant_info)
            else:
                print(Fore.RED + f"Pembelian bibit tanaman gagal. Status Code: {response.status_code}")
    
    return selected_plants


def display_choices():
    choices = {
        1: ("Tomat 🍅", 13, 1000.0),
        2: ("Carrot 🥕", 14, 2000.0),
        3: ("Pineapple 🍍", 15, 4000.0),
        4: ("Watermelon 🍉", 16, 8000.0),
        5: ("Grape 🍇", 17, 16000.0),
        6: ("Rose 🌹", 18, 500.0),  # Tambah Rose
        7: ("Potato 🥔", 19, 1000.0)  # Tambah Potato
    }
    print(Fore.WHITE + f"\n=============== Shop Bibit ===============")
    for num, (name, _, _) in choices.items():
        print(Fore.WHITE + f"{num}. {name}")
    return choices


def get_accounts(filename):
    with open(filename, "r") as file:
        return [line.strip() for line in file if line.strip()]        

def countdown_timer(duration, message):
    while duration > 0:
        mins, secs = divmod(duration, 60)
        timeformat = f"{mins:02d}:{secs:02d}"
        print(Fore.YELLOW + f"\r{message}: {timeformat}", end="")
        time.sleep(1)
        duration -= 1
    print("\n")

def beli_bibit_jika_diperlukan(access_token, empty_land, plant_data, backup_stock, gem):
    num_empty_land = len(empty_land)
    num_available_plants = len(plant_data)

    if num_available_plants < num_empty_land:
        print(Fore.YELLOW + "Tidak cukup bibit untuk semua lahan kosong. Menggunakan cadangan bibit...")
        num_needed = num_empty_land - num_available_plants

        if len(backup_stock) >= num_needed:
            plant_data.extend(backup_stock[:num_needed])
            backup_stock = backup_stock[num_needed:]
            print(Fore.GREEN + f"Menggunakan {num_needed} bibit dari cadangan.")
        else:
            plant_data.extend(backup_stock)
            num_needed -= len(backup_stock)
            backup_stock = []
            print(Fore.YELLOW + f"Hanya {len(plant_data)} bibit dari cadangan yang tersedia. Membeli lebih banyak bibit...")

        num_seeds_to_buy = max(num_needed, len(empty_land))
        # Pass gem to the buy_plant function
        purchased_plants = buy_plant(access_token, num_seeds_to_buy, gem)

        if purchased_plants:
            backup_stock.extend(purchased_plants[num_needed:])
            plant_data.extend(purchased_plants[:num_needed])
            print(Fore.GREEN + f"{len(purchased_plants)} bibit tambahan berhasil dibeli, dengan {len(backup_stock)} bibit cadangan tersedia.")
        else:
            print(Fore.RED + "Gagal membeli bibit tambahan.")
    else:
        print(Fore.GREEN + "Bibit sudah mencukupi untuk semua lahan kosong.")
    
    return plant_data, backup_stock

def tanam_bibit(access_token, empty_land, plant_data):
    if not empty_land:
        print(Fore.YELLOW + "Tidak ada lahan kosong yang tersedia.")
        return
    
    for idx, land in enumerate(empty_land):
        if idx < len(plant_data):
            selected_plant = plant_data[idx]
            plant_id = selected_plant['id']
            land_id = land['id']
            
            nanam_with_retry(access_token, plant_id, land_id)
        else:
            print(Fore.YELLOW + "Bibit tidak cukup untuk semua lahan kosong.")
            break

def prepare_buy_pet(access_token, store_id, price, unit, golden_coin):
    if golden_coin < 1_000_000:
        print(Fore.RED + "Golden Coin kurang dari 1 juta. Tidak dapat membeli hewan.")
        return None
    
    url = "https://api.catopia.io/api/v1/store/buy"
    headers = create_headers(access_token)
    body = {
        "storeId": store_id,
        "price": price,
        "unit": unit
    }

    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 201:
        print(Fore.GREEN + "Pembelian hewan berhasil")
        global animal_bought
        animal_bought = True  # Mark that an animal was bought
        return response.json()
    else:
        print(Fore.RED + f"Pembelian hewan gagal. Status Code: {response.status_code}")
        return None

# Functions for saving, loading, and removing special chest IDs from the file
def save_special_chest_ids_to_file(type_id_chest_pairs, filename="kotakhewan.txt"):
    with open(filename, "a") as file:
        for type_id, chest_id in type_id_chest_pairs:
            file.write(f"{type_id},{chest_id}\n")
    print(Fore.GREEN + f"ID chest dan pasangan typeId berhasil disimpan ke {filename}.")

def load_special_chest_ids_from_file(filename="kotakhewan.txt"):
    if not os.path.exists(filename):
        return []
    with open(filename, "r") as file:
        return [tuple(line.strip().split(',')) for line in file]

def remove_successful_pairs_from_file(successful_pairs, filename="kotakhewan.txt"):
    existing_pairs = load_special_chest_ids_from_file(filename)
    remaining_pairs = [pair for pair in existing_pairs if pair not in successful_pairs]
    
    with open(filename, "w") as file:
        for pair in remaining_pairs:
            file.write(f"{pair[0]},{pair[1]}\n")
    print(Fore.GREEN + f"Data pasangan typeId dan ID chest yang sukses telah dihapus dari {filename}.")

def get_special_chest_ids(access_token, limit=3000):
    url = "https://api.catopia.io/api/v1/players/chest"
    headers = create_headers(access_token)
    params = {"limit": limit}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json().get('data', [])
        chest_ids = [item['id'] for item in data]  # Now just focus on getting the chest IDs
        print(Fore.CYAN + f"Chest IDs retrieved: {len(chest_ids)} available.")
        
        return chest_ids
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Error retrieving chest IDs: {e}")
        return []

def buy_pets(access_token, pet_type_ids, chest_ids):
    url = "https://api.catopia.io/api/v1/chest/open-multiple"
    headers = create_headers(access_token)
    payload = {
        "petTypeIds": pet_type_ids,
        "chestIds": chest_ids
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        return response.json()
    else:
        response.raise_for_status()

def perform_pet_purchase_during_harvest(access_token, filename="kotakhewan.txt"):
    # Load saved chest and type ID pairs from file
    chest_type_pairs = load_special_chest_ids_from_file(filename)
    
    if not chest_type_pairs:
        print(Fore.YELLOW + "Tidak ada pasangan typeId dan chest ID yang tersimpan untuk pembelian.")
        return

    successful_pairs = []
    error_pairs = []
    
    # Iterate over the saved pairs and attempt to purchase pets
    for type_id, chest_id in chest_type_pairs:
        print(Fore.WHITE + f"Mencoba untuk membeli pet dengan typeId {type_id} dan chestId {chest_id}.")
        
        try:
            response = buy_pets(access_token, [type_id], [chest_id])
            if response.get('success'):
                print(Fore.GREEN + f"Pembelian pet berhasil untuk typeId {type_id} dan chestId {chest_id}.")
                successful_pairs.append((type_id, chest_id))  # Tandai pasangan yang sukses
            else:
                print(Fore.RED + f"Gagal membeli pet dengan typeId {type_id} dan chestId {chest_id}.")
                error_pairs.append((type_id, chest_id))  # Tandai pasangan yang gagal
        except Exception as e:
            print(Fore.RED + f"Error saat mencoba membeli pet untuk typeId {type_id} dan chestId {chest_id}: {e}")
            error_pairs.append((type_id, chest_id))  # Tandai pasangan yang gagal karena error
    
    # Hapus semua pasangan dari file (baik sukses maupun gagal)
    if successful_pairs or error_pairs:
        remove_successful_pairs_from_file(chest_type_pairs, filename)  # Hapus semua pasangan
        print(Fore.CYAN + "Semua pasangan typeId dan chestId telah dihapus dari file.")
    else:
        print(Fore.YELLOW + "Tidak ada pembelian yang berhasil atau gagal. Tidak ada pasangan yang dihapus.")


def upgrade_pet(access_token, level, pet_type_id):
    """
    Menaikkan level hewan dengan `typeId` tertentu.
    """
    url = "https://api.catopia.io/api/v1/players/pet/fast-upgrade"
    headers = create_headers(access_token)
    payload = {
        "level": level,
        "petTypeId": pet_type_id
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Menangani error HTTP
        return response.json()
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Error upgrading pet type ID {pet_type_id} at level {level}: {e}")
        return None

def get_pets_to_upgrade(access_token):
    """
    Mengambil data hewan yang tersedia untuk di-upgrade.
    """
    url = "https://api.catopia.io/api/v1/players/pet?limit=3000"
    headers = create_headers(access_token)
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Menangani error HTTP
        pets = response.json().get('data', [])
        return pets
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Error fetching pets for upgrade: {e}")
        return []


def find_pets_to_level_up(pets, required_count=5):
    pets_grouped = {}
    for pet in pets:
        key = (pet['name'], pet['level'])
        if key not in pets_grouped:
            pets_grouped[key] = []
        pets_grouped[key].append(pet)
    
    eligible_pets = []
    for group in pets_grouped.values():
        if len(group) >= required_count:
            eligible_pets.extend(group[:required_count])
            break
    
    return eligible_pets

def get_type_id_by_name(name):
    mapping = {
        "Dogecoin": 1,
        "Bonk": 15,
        "Brett": 13,
        "Mog": 8,
        "Smog": 10,
        "Floki": 12,
        "dogwifhat": 11,
        "Pepe": 14,
        "cat in a dogs world": 3,
        "Myro": 6,
        "Shiba Inu": 2,
        "BOOK OF MEME": 9,
        "Slerf": 5,
        "Wen": 7,
        "COQ INU": 4
    }
    return mapping.get(name)

def upgrade_pet_sequentially(access_token, pet_type_id):
    current_level = 1  # Start from level 1
    while True:
        try:
            upgrade_response = upgrade_pet(access_token, current_level, pet_type_id)
            if upgrade_response.get('success'):
                print(Fore.GREEN + f"Level {current_level} upgrade successful for pet type ID {pet_type_id}.")
                current_level += 1  # Move to the next level if successful
            else:
                print(Fore.RED + f"Upgrade failed at level {current_level} for pet type ID {pet_type_id}. Moving to the next pet.")
                break  # Stop upgrading if it fails
        except Exception as e:
            print(Fore.RED + f"Error upgrading pet type ID {pet_type_id} at level {current_level}: {e}")
            break

def upgrade_pet_with_error_handling(access_token, pet_type_id):
    if not animal_bought:
        print(Fore.RED + "Tidak ada hewan yang dibeli. Tidak dapat menaikkan level hewan.")
        return
    
    current_level = 1  # Mulai dari level 1
    while True:
        try:
            upgrade_response = upgrade_pet(access_token, current_level, pet_type_id)
            if upgrade_response.get('success'):
                print(Fore.GREEN + f"Level {current_level} upgrade successful for pet type ID {pet_type_id}.")
                current_level += 1  # Jika berhasil, naik ke level berikutnya
            else:
                print(Fore.RED + f"Upgrade failed at level {current_level} for pet type ID {pet_type_id}. Moving to the next pet.")
                break  # Berhenti jika gagal
        except Exception as e:
            print(Fore.RED + f"Error upgrading pet type ID {pet_type_id} at level {current_level}: {e}")
            break

def process_pets_for_upgrade(access_token):
    """
    Proses utama untuk menaikkan level hewan.
    Hanya memproses `typeId` antara 1 dan 15, serta tidak mengulangi `typeId` yang sudah diproses.
    """
    pets = get_pets_to_upgrade(access_token)  # Mendapatkan data hewan dari API
    processed_type_ids = set()  # Menyimpan `typeId` yang sudah diproses

    for pet in pets:
        type_id = pet['typeId']  # Menggunakan langsung `typeId` dari respon API

        # Memproses hanya `typeId` antara 1 dan 15 serta memastikan tidak diulang
        if 1 <= type_id <= 15 and type_id not in processed_type_ids:
            print(Fore.WHITE + f"Attempting to upgrade pet with typeId {type_id}")
            upgrade_pet_with_error_handling(access_token, type_id)
            processed_type_ids.add(type_id)  # Menandai bahwa `typeId` sudah diproses
        else:
            print(Fore.YELLOW + f"Skipping pet with typeId {type_id}. Either out of range or already processed.")


def claim_animal_income(access_token):
    url = "https://api.catopia.io/api/v1/user-collection/claim-gold"
    headers = create_headers(access_token)
    
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        
        if response.json().get('success'):
            claimed_coin = response.json().get('data', {}).get('claimedCoin', 0)
            print(Fore.GREEN + f"Berhasil mengklaim penghasilan dari hewan: {claimed_coin} Golden Coin.")
            return claimed_coin
        else:
            print(Fore.RED + "Gagal mengklaim penghasilan dari hewan.")
            return 0
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Error during claim animal income request: {e}")
        return 0

def get_daily_missions(access_token):
    url = "https://api.catopia.io/api/v1/user/daily-mission?limit=3000"
    headers = create_headers(access_token)
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json().get('data', [])
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Error during get daily missions request: {e}")
        return []

def claim_mission_reward(access_token, mission_id):
    url = f"https://api.catopia.io/api/v1/user/daily-mission/{mission_id}/claim"
    headers = create_headers(access_token)
    
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        
        if response.json().get('success'):
            print(Fore.GREEN + f"Berhasil mengklaim hadiah untuk misi {mission_id}.")
        else:
            print(Fore.RED + f"Gagal mengklaim hadiah untuk misi {mission_id}.")
    except requests.exceptions.RequestException as e:
        print(Fore.RED + f"Error during claim mission reward request: {e}")

def farming_logic(access_token):
    try:
        pets = get_pets_to_upgrade(access_token)
        process_pets_for_upgrade(access_token)  # Automate upgrading all pets sequentially
    except Exception as e:
        print(Fore.RED + f"Error during pet upgrade process: {e}")

    try:
        empty_land, occupied_land = land(access_token)
    except Exception as e:
        print(Fore.RED + f"Gagal mendapatkan data lahan: {e}")
        empty_land, occupied_land = [], []

    try:
        plant_data = plant(access_token)
    except Exception as e:
        print(Fore.RED + f"Gagal mendapatkan data bibit: {e}")
        plant_data = []

    backup_stock = []
    try:
        # Collect user's resources to pass gem and golden_coin into the necessary functions
        golden_coin, gem, _ = collect(access_token)
        
        plant_data, backup_stock = beli_bibit_jika_diperlukan(access_token, empty_land, plant_data, backup_stock, gem)
    except Exception as e:
        print(Fore.RED + f"Gagal membeli bibit: {e}")

    try:
        tanam_bibit(access_token, empty_land, plant_data)
    except Exception as e:
        print(Fore.RED + f"Gagal menanam bibit: {e}")

    try:
        claim_animal_income(access_token)
    except Exception as e:
        print(Fore.RED + f"Gagal mengklaim pendapatan dari hewan: {e}")

    try:
        daily_missions = get_daily_missions(access_token)
        for mission in daily_missions:
            if mission['isCompleted'] and not mission['claimed']:
                try:
                    claim_mission_reward(access_token, mission['id'])
                except Exception as e:
                    print(Fore.RED + f"Gagal mengklaim hadiah untuk misi {mission['id']}: {e}")
    except Exception as e:
        print(Fore.RED + f"Gagal mendapatkan atau mengklaim misi harian: {e}")

    all_harvested = True
    next_harvest_times = []
    try:
        if occupied_land:
            for item in occupied_land:
                if item['plantedAt'] is not None:
                    land_id = item['id']
                    planted_id = item['plantId']
                    planted_at = item['plantedAt']
                    duration = item.get('duration')

                    remaining_seconds = duration - (datetime.now() - parse_datetime(planted_at)).total_seconds()

                    if duration and is_time_to_harvest(planted_at, duration, remaining_seconds):
                        try:
                            harvest_data = panen(access_token, planted_id, land_id)
                            if harvest_data and harvest_data.get('statusCode') == 201:
                                print(Fore.GREEN + f"Panen pada lahan {land_id} berhasil.")
                            else:
                                print(Fore.RED + f"Panen pada lahan {land_id} gagal.")
                                all_harvested = False
                        except Exception as e:
                            print(Fore.RED + f"Gagal memanen pada lahan {land_id}: {e}")
                            all_harvested = False
                    else:
                        next_harvest_times.append(parse_datetime(planted_at) + timedelta(seconds=duration))
                        all_harvested = False
                        print(Fore.YELLOW + f"Belum waktunya panen pada lahan {land_id}.")
        else:
            print(Fore.YELLOW + "Tidak ada data lahan nanam.")
    except Exception as e:
        print(Fore.RED + f"Kesalahan dalam proses panen: {e}")

    try:
        if all_harvested:
            # Pass golden_coin when calling prepare_buy_pet
            prepare_buy_pet_response = prepare_buy_pet(access_token, store_id=4, price=60000, unit=1, golden_coin=golden_coin)
            if prepare_buy_pet_response:
                print(Fore.GREEN + "Akun telah dipersiapkan untuk pembelian hewan.")

            special_chest_ids = get_special_chest_ids(access_token)
            type_id_chest_pairs = [(random.randint(1, 15), chest_id) for chest_id in special_chest_ids]

            save_special_chest_ids_to_file(type_id_chest_pairs)

            # Perform pet purchase using the saved chest IDs
            perform_pet_purchase_during_harvest(access_token)
        else:
            print(Fore.YELLOW + "Tidak semua tanaman telah dipanen. Menunggu panen sebelum membeli hewan.")
    except Exception as e:
        print(Fore.RED + f"Gagal dalam proses persiapan atau pembelian hewan: {e}")

    try:
        empty_land_after_harvest, _ = land(access_token)
        if len(plant_data) >= len(empty_land_after_harvest):
            tanam_bibit(access_token, empty_land_after_harvest, plant_data)
        # Pass gem when calling beli_bibit_jika_diperlukan
        plant_data, backup_stock = beli_bibit_jika_diperlukan(access_token, empty_land_after_harvest, plant_data, backup_stock, gem)
    except Exception as e:
        print(Fore.RED + f"Kesalahan dalam proses penanaman atau pembelian bibit setelah panen: {e}")

def main():
    accounts = get_accounts("init.txt")
    total_accounts = len(accounts)
    print(Fore.WHITE + f"Total Akun: {total_accounts}")

    while True:
        next_harvest_times = []

        for idx, init_data in enumerate(accounts):
            print(Fore.CYAN + f"\n=============== Memproses Akun {idx + 1} dari {total_accounts} ===============")

            # Retry login up to 3 times per account
            for attempt in range(3):
                access_token, refresh_token = login(init_data)
                if access_token:
                    break  # Exit retry loop if login is successful
                else:
                    print(Fore.RED + f"Login failed for account {idx + 1}. Attempt {attempt + 1} of 3.")
                    time.sleep(2)  # Short delay before retrying
            else:
                print(Fore.RED + f"Skipping account {idx + 1} after 3 failed login attempts.")
                continue  # Skip this account if login fails after 3 attempts

            if access_token:
                try:
                    full_name, level = get_user_info(access_token)
                    print(Fore.WHITE + f"\n=============== Detail Akun ===============")
                    print(Fore.WHITE + f"Name: {full_name}")
                    print(Fore.WHITE + f"Level: {level}")
                except requests.exceptions.RequestException as e:
                    print(Fore.RED + f"An error occurred while retrieving user info: {e}")

                try:
                    golden_coin, gem, boost_settings = collect(access_token)
                    print(Fore.WHITE + f"Golden Coin: {golden_coin}")
                    print(Fore.WHITE + f"Gem: {gem}")
                except requests.exceptions.RequestException as e:
                    print(Fore.RED + f"An error occurred while retrieving collection data: {e}")

                try:
                    farming_logic(access_token)
                except requests.exceptions.RequestException as e:
                    print(Fore.RED + f"An error occurred while executing farming logic: {e}")

            time.sleep(5)

        if next_harvest_times:
            min_harvest_time = min(next_harvest_times)
            remaining_seconds = (min_harvest_time - datetime.now()).total_seconds()
            remaining_seconds = max(remaining_seconds, 0)
            print(Fore.YELLOW + f"Semua akun telah diproses. Menunggu hingga panen berikutnya.")
            countdown_timer(int(remaining_seconds), "Hitung mundur hingga panen berikutnya")
        else:
            print(Fore.YELLOW + "Semua akun telah diproses. menunggu pemrosesan ulang.")
            countdown_timer(200, "Hitung mundur hingga pemrosesan ulang")

if __name__ == "__main__":
    main()
