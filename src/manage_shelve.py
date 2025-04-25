import shelve
import os

SIGNALS_DB = os.path.join('data', 'trade_signals')
TRADES_POSITIONS_DB = os.path.join('data', 'signals_and_positions')

def store_data(dbName, key, value):
    with shelve.open(dbName) as db:
        db[key] = value

def get_item(dbName, key):
    with shelve.open(dbName) as db:
        try:
            return db[key]
        except KeyError:
            return

def show_all_data(dbName):
    with shelve.open(dbName) as db:
        for key, value in db.items():
            print(f'Sleutel: {key}, Waarde: {value}')

def get_most_recent(dbName):
    with shelve.open(dbName) as db:
        sorted_keys = sorted(db.keys(), key=int) 
        if sorted_keys:
            # Haal de hoogste sleutel op
            highest_key = sorted_keys[-1]
            highest_value = db[highest_key]
    
    return highest_key, highest_value

if __name__ == "__main__":
    key = '34224'
    value = [1, 2, 3, 4]
    store_data(SIGNALS_DB, key, value)
    value.append(1000)
    store_data(SIGNALS_DB, key, value)

    item = get_item(SIGNALS_DB, '234234')
    if item:
        print(item)
    else:
        print('niets gevonden') 
    show_all_data(SIGNALS_DB)
    highest = get_most_recent(SIGNALS_DB)
    print(highest)
    print(type(highest))
