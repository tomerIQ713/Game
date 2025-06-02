# ChessMaster – Multiplayer Chess Game with AI Analysis

**ChessMaster** is a secure, full-featured multiplayer chess game built with Python and Pygame. The app uses a client-server architecture to enable real-time gameplay between users, and integrates the powerful AI engine to analyze your games after completion.

##  Features

-  Real-time multiplayer chess matches (client-server)
-  Secure login and user authentication system
-  Post-game analysis with Stockfish (best move suggestions and mistakes)
-  Full chess rule support: castling, en passant, promotion, and checkmate
-  Clean and responsive Pygame GUI
-  Add friends and challenge them

## Technologies Used

- Python (**Socket, Threading, OOP**)
- Pygame for GUI
- Chess engine analysis
- **SQLite / JSON / File I/O** for data persistence


## Installation

- Download the files.
- Run the `install_dependencies.bat` file to download the necessary libraries.
- Download Stockfish from `https://stockfishchess.org/download/`
- Unzip the Stockfish file
- Move the Stockfish folder into the `Game` folder.
- In the `Stockfish` folder, Rename the file that ends with `.exe` to `stockfish.exe`

## SETUP
  **AS A SERVER** 
  - In wherever computer you want to run the server in,
    check its **IP adress** using the command `ipconfig`.
  - In `server/server.py` Replace the IP adress in the `__init__` function with your IP adress.

  **AS A CLIENT**
  - In the `pages` folder, open the `login_page.py` file, and replace the IP in the `__init__` function with the server IP.


## How to play
- Open the `Game` folder in VS-Code or any other python compiler.
- Open the `server` folder and run the `server.py` file.
- In the main path, run `main.py` file.
- **If you want to have another player against you**, run the `main.py` file again, in the other computer or in yours.
- Keep in mind, if you run the server and 2 clients on one PC, it can have a strain on your computer.
  **Make sure you write the IP address correctly**.




