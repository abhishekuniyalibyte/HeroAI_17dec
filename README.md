create env: python3.12 -m venv venv
act env: venv/bin/activate

TERMINAL 1: ((venv) ) abhishek@abhishek-desktop:~/Documents/HeroAI 17dec$ python manage.py runserver
TERMINAL 2: ((venv) ) abhishek@abhishek-desktop:~/Documents/HeroAI 17dec$ celery -A restaurant_backend worker -l info


-> FIX UI PART
-> ADD 'ADD TO CART FEATURE'  
-> view cart -> create a new file for it
-> CHATBOT IS GIVING MENU RESPONSE 2 TIME
-> ADD TODAY'S SPECIAL IN CHATBOT


-> IF CLIENT IS INTEGRATED WITH OUT SYSTEM POS, then send data to our database otherwise send it with Whatsapp.
-> single database for all Res Menu file.

-> restaurant/ menu_extractor.py
-> chatbot/ chatbot.py
-> media/ json + embeddding
-> templates/  UI part
-> chatbot/ view.py  from line of code  numebr 333, 452 - Post Request
-> db.sqlite = database