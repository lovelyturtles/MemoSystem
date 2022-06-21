# Assignment 2

For this project we are creating our own webserver. We also make a client to simulate requests. 

## How to Run the Code
Please log into aviary to run my server. I have also hardcoded goose in my web client so please use these steps:
1. ssh into goose.cs.umanitoba.ca
2. Go into the assignment directory 
3. Run the server.py file with ```python3 server.py```
4. Open some browser anywhere and type in goose.cs.umanitoba.ca:8265 to get to the index page (you have to be logged into the University of Manitoba vpn
5. From here you can add your back slashes and filenames to get to whatever page you're looking to get to. As an example ```loon.cs.umanitoba.ca:8265/images.html```

## Issues
* The javascript client is very buggy but if you type in something like loon.cs.umanitoba.ca:8265/get/api into your web browser, you'll be able to see the requests come in on your server
* POST has not been implemented and DELETE is not working because of formatting issues
* If you exit my server with Control C before you close the browser, you'll have to press Control C again for the program to actually close. 